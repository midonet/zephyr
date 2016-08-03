# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common import file_location
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import get_class_from_fqn
from zephyr.common import zephyr_constants
from zephyr_ptm.ptm.application.netns_hv import NetnsHV
from zephyr_ptm.ptm.fixtures import midonet_setup_fixture
from zephyr_ptm.ptm.fixtures import neutron_setup_fixture
from zephyr_ptm.ptm.physical_topology_config import PhysicalTopologyConfig


class PhysicalTopologyManager(object):
    def __init__(self, root_dir='.', log_manager=None, log_root_dir=None):
        self.hosts_by_name = {}
        """ :type: dict[str, ptm.host.host.Host]"""
        self.host_by_start_order = []
        """ :type: list[list[ptm.host.host.Host]]"""
        self.hypervisors = {}
        """ :type: dict[str, list[HypervisorService|Application]]"""
        self.virtual_network_hosts = {}
        """ :type dict[str, ptm.host.host.Host]"""
        self.neutron_setup = neutron_setup_fixture.NeutronSetupFixture(
            self)
        # TODO(micucci) Remove this from base PTM.  This needs to be
        # an extension.
        self.midonet_setup = midonet_setup_fixture.MidonetSetupFixture(
            self)
        self.root_dir = root_dir
        if not log_root_dir:
            log_root_dir = self.root_dir
        self.LOG = logging.getLogger('ptm-null-root')
        self.LOG.addHandler(logging.NullHandler())
        self.CONSOLE = logging.getLogger('ptm-null-console')
        self.CONSOLE.addHandler(logging.NullHandler())
        self.log_level = logging.INFO
        self.debug = False
        self.log_manager = (log_manager
                            if log_manager is not None
                            else LogManager(root_dir=log_root_dir))
        """ :type: LogManager"""
        self.log_file_name = zephyr_constants.ZEPHYR_LOG_FILE_NAME
        self.fixtures = {}
        """ :type: dict[str, ServiceFixture]"""
        self.config_file = None
        self.hosts = []
        self.topo_file = None

    def configure_logging(self, log_file_name=None,
                          log_name='ptm-root', debug=False):
        self.log_level = logging.DEBUG if debug is True else logging.INFO
        self.debug = debug
        if log_file_name:
            self.log_file_name = log_file_name

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(
                file_name=self.log_file_name,
                name=log_name + '-debug',
                file_log_level=self.log_level,
                stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(
                file_name=self.log_file_name,
                name=log_name,
                log_level=self.log_level)

        self.CONSOLE = self.log_manager.add_stdout_logger(
            name=log_name + '-console', log_level=logging.INFO)

        # Update all loggers for all configured hosts
        for host in self.hosts_by_name.itervalues():
            host.set_log_level(self.log_level)

        self.neutron_setup.configure_logging(self.LOG)
        self.midonet_setup.configure_logging(self.LOG)

    def configure(self, config_file, file_type='json',
                  config_dir=None):
        """
        IMPORTANT NOTE!!!  For Hosts and for Applications, the
        implementation class name in the [implementation] section
        MUST have the class's name be the same name as the last
        dotted-name in the module (the string after the last
        dot (.), without the .py extension)!

        :param config_file: str
        :param file_type: str
        :param config_dir: str
        :return:
        """
        self.LOG.debug('**ptm configuration started**')
        self.LOG.debug('Configuring ptm with file: ' + config_file)
        # TODO(micucci): Enable multiple config files to define roots
        # across several Linux hosts
        self.config_file = config_file
        default_cfg_path = '/zephyr_ptm/ptm/config/physical_topologies'

        if self.config_file.startswith('/'):
            config_dir = '/'

        full_path_config_file = (
            (config_dir
             if config_dir
             else (self.root_dir + default_cfg_path)) +
            '/' + config_file)

        config_obj = None
        self.topo_file = full_path_config_file
        with open(full_path_config_file, 'r') as f:
            if file_type == 'json':
                config_obj = json.load(f)
            else:
                raise exceptions.InvalidConfigurationException(
                    full_path_config_file,
                    'Could not open file of type: ' + file_type)

        self.LOG.debug('Read JSON, configure object=' + str(config_obj))
        ptc = PhysicalTopologyConfig.make_physical_topology(config_obj)

        # We need a root server to act as the "local host" with
        # access to the base Linux OS
        if 'root' not in ptc.hosts or 'root' not in ptc.implementation:
            raise exceptions.ObjectNotFoundException(
                'Physical Topology must have one host and '
                'implementation for "root"')

        self.LOG.debug('Configuring ptm host setup')
        # Configure each host in the configuration with its name
        # and bridge/interface
        # definitions
        for host_cfg in ptc.hosts.itervalues():

            if host_cfg.name not in ptc.implementation:
                raise exceptions.ObjectNotFoundException(
                    'No implementation for host: ' + host_cfg.name)

            # Get the impl details and use that to instance a basic object
            impl_cfg = ptc.implementation[host_cfg.name]

            self.LOG.debug('Configuring host: ' + host_cfg.name +
                           ' with impl: ' + impl_cfg.impl)
            h = get_class_from_fqn(impl_cfg.impl)(host_cfg.name, self)
            """ :type h: Host"""
            h.configure_logging(log_file_name=self.log_file_name,
                                debug=self.debug)
            self.hosts_by_name[h.name] = h

            self.LOG.debug('Configuring individual host:' + h.name)
            # Now configure the host with the definition and impl configs
            h.config_from_ptc_def(host_cfg, impl_cfg)

            if h.is_virtual_network_host():
                self.virtual_network_hosts[h.name] = h
                self.LOG.debug('Adding host to VN host list:' + h.name)

            for a in h.applications:
                if isinstance(a, NetnsHV):
                    self.LOG.debug(
                        'Adding host application to hypervisor list:' +
                        h.name + '/' + a.__class__.__name__)
                    if h.name not in self.hypervisors:
                        self.hypervisors[h.name] = []
                    self.hypervisors[h.name].append(a)

        # After the hosts are all added and configured, we can cross-reference
        # any mention of hosts in the wiring config and build a map that links
        # near host/interface to a far host object and with its interface
        # definition.n

        # The wire config looks like this:
        # {
        #   'host1': {
        #     'eth0': { host: 'hostz' interface: 'eth0' }
        #     'eth1': { host: 'hosty' interface: 'eth0' }
        #   }
        #  'host2': {
        #     'eth0': { host: 'hostx' interface: 'eth0' }
        #     ... and so on

        # This means we can give each host a map of interfaces to far host
        # and interface objects:
        # {
        #   'eth0': { host: Host() for 'hostz' iface: Interface() for 'eth0' }
        #   'eth1': { host: Host() for 'hosty' iface: Interface() for 'eth0' }
        #   ... and so on
        # }
        #
        # This map can be used to wire hosts to each other

        for host in self.hosts_by_name.itervalues():

            self.LOG.debug('Connecting host based on wiring scheme:' +
                           host.name)
            # If host has a map entry for wiring, configure the wiring map
            # for that host If not, then skip any wiring configuration.
            if host.name in ptc.wiring:
                for if_name, wire in ptc.wiring[host.name].iteritems():
                    if if_name not in host.interfaces:
                        raise exceptions.ObjectNotFoundException(
                            'No near interface ' + if_name +
                            ' found for connection from host ' + host.name)

                    near_iface = host.interfaces[if_name]

                    if wire.host not in self.hosts_by_name:
                        raise exceptions.ObjectNotFoundException(
                            'No far host ' + wire.host +
                            ' found for connection from host ' + host.name)
                    far_host = self.hosts_by_name[wire.host]

                    if wire.interface not in far_host.interfaces:
                        raise exceptions.ObjectNotFoundException(
                            'No far interface ' + wire.interface +
                            ' found for connection from host ' + host.name)

                    far_iface = far_host.interfaces[wire.interface]

                    self.LOG.debug(
                        'Link found:' + host.name + '/' + near_iface.name +
                        ' -> ' + far_host.name + '/' + far_iface.name)

                    host.link_interface(near_iface, far_host, far_iface)

        for name in ptc.host_start_order:
            self.LOG.debug('Adding host name or list to start list: ' +
                           str(name))
            if isinstance(name, list):
                tier_list = []
                for host in name:
                    if host not in self.hosts_by_name:
                        raise exceptions.ObjectNotFoundException(
                            'Cannot set start order: host ' + host +
                            ' not found')
                    tier_list.append(self.hosts_by_name[host])
                self.host_by_start_order.append(tier_list)
                pass
            else:
                if name not in self.hosts_by_name:
                    raise exceptions.ObjectNotFoundException(
                        'Cannot set start order: host ' + name +
                        ' not found')
                self.host_by_start_order.append([self.hosts_by_name[name]])

        cli.LinuxCLI().cmd('chmod 755 /var/log/neutron')
        cli.LinuxCLI().cmd('chmod 644 /var/log/neutron/neutron-server.log')
        self.log_manager.add_external_log_file(
            file_location.FileLocation('/var/log/neutron/neutron-server.log'),
            '', '%Y-%m-%d %H:%M:%S.%f')
        self.LOG.debug('**ptm configuration finished**')

    def print_config(self, indent=0, logger=None):
        print('Hosts (in start-order):')
        for l in self.host_by_start_order:
            for h in l:
                h.print_config(indent + 1)

    def startup(self):
        """
        Startup the configured Midonet cluster, including creating,
        booting, initializing, and starting all hosts
        :return:
        """
        self.LOG.debug('**ptm starting up**')

        self.LOG.debug('ptm starting hosts')
        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm creating host: ' + h.name)
                h.create()

        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm booting host: ' + h.name)
                h.boot()

        self.LOG.debug('ptm starting host network')
        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm starting networks on host: ' + h.name)
                h.net_up()

        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm finalizing networks on host: ' + h.name)
                h.net_finalize()

        self.LOG.debug('ptm starting host applications')
        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm preparing config files on host: ' + h.name)
                h.prepare_applications(self.log_manager)

        for l in self.host_by_start_order:
            for h in l:
                self.LOG.debug('ptm starting apps on host: ' + h.name)
                h.start_applications()

            for h in l:
                self.LOG.debug('ptm waiting for apps to start on host: ' +
                               h.name)
                h.wait_for_all_applications_to_start()

        # Must go through and set up both neutron and
        # midonet for use by zephyr.
        # TODO(micucci) Remove the midonet-specific setup and put it in an
        # extension
        self.midonet_setup.setup()
        self.neutron_setup.setup()

        self.LOG.debug('**ptm startup finished**')

    def shutdown(self):
        """
        Shutdown the configured Midonet cluster by stopping, shutting
        own, and removing all hosts
        :return:
        """
        self.LOG.debug('**ptm shutting down**')
        for l in reversed(self.host_by_start_order):
            for h in l:
                try:
                    self.LOG.debug('ptm stopping apps on host: ' + h.name)
                    h.stop_applications()
                except Exception as e:
                    self.LOG.fatal('Fatal error shutting down ptm host apps, '
                                   'trying to continue to next host: ' +
                                   str(e))

        for l in reversed(self.host_by_start_order):
            for h in l:
                self.LOG.debug('ptm waiting for apps to stop on host: ' +
                               h.name)
                h.wait_for_all_applications_to_stop()

        self.LOG.debug('ptm stopping networks')
        for l in reversed(self.host_by_start_order):
            for h in l:
                try:
                    self.LOG.debug('ptm bringing down network on host: ' +
                                   h.name)
                    h.net_down()
                except Exception as e:
                    self.LOG.fatal(
                        'Fatal error shutting down ptm host '
                        'networks, trying to continue to next host: ' +
                        str(e))

        self.LOG.debug('ptm stopping hosts')
        for l in reversed(self.host_by_start_order):
            for h in l:
                try:
                    self.LOG.debug('ptm stopping host: ' + h.name)
                    h.shutdown()
                except Exception as e:
                    self.LOG.fatal(
                        'Fatal error shutting down ptm hosts, trying '
                        'to continue to next host: ' +
                        str(e))

        for l in reversed(self.host_by_start_order):
            for h in l:
                try:
                    self.LOG.debug('ptm deleting host: ' + h.name)
                    h.remove()
                except Exception as e:
                    self.LOG.fatal(
                        'Fatal error removing ptm hosts, trying to '
                        'continue to next host: ' +
                        str(e))

        self.neutron_setup.teardown()
        self.LOG.debug('**ptm shutdown finished**')

    def ptm_host_app_control(self, app_cmd, host_json, app_json, arg_list):

        self.LOG.debug('Running app command: ' + app_cmd)
        self.LOG.debug('Loading JSON for host: ' + host_json)
        self.LOG.debug('Loading JSON for app: ' + app_json)

        host_cfg_map = json.loads(host_json)
        app_cfg_map = json.loads(app_json)

        host_name = host_cfg_map['name']

        host_impl_class = get_class_from_fqn(host_cfg_map['impl'])
        host_log_file = host_cfg_map.get(
            'log_file_name',
            zephyr_constants.ZEPHYR_LOG_FILE_NAME)
        app_impl_class = get_class_from_fqn(app_cfg_map['class'])
        app_log_file = app_cfg_map.get(
            'log_file_name',
            zephyr_constants.ZEPHYR_LOG_FILE_NAME)

        h = host_impl_class(host_name, self)
        """ :type: Host"""
        a = app_impl_class(h)
        """ :type: Application"""

        h.configure_logging(log_file_name=host_log_file,
                            debug=False)
        a.configure_logging(log_file_name=app_log_file,
                            debug=False)

        a.config_app_for_process_control(app_cfg_map)
        a.prepare_environment()

        if app_cmd == 'start':
            a.control_start()
        elif app_cmd == 'stop':
            a.control_stop()
        else:
            fn_name = 'control_' + app_cmd
            fn = getattr(a, fn_name)
            if fn is not None:
                fn(*arg_list)
            else:
                raise exceptions.ArgMismatchException(
                    'Command implementation function not '
                    'found on app class: ' +
                    app_cfg_map['class'] + '.' + fn_name)

        a.cleanup_environment()
        self.LOG.debug("ptm-host-ctl finished")

    def get_topology_features(self):
        return {'dhcp_on_vms': True,
                'compute_hosts': len(self.hypervisors),
                'edge_hosts': len([h for h in self.hosts_by_name.iterkeys()
                                   if h.startswith('edge')]),
                'host_names': [h for h in self.hosts_by_name.iterkeys()]}

    def get_topology_feature(self, feature):
        """
        Known topology features across all ptm types:

        compute_hosts: Number of compute nodes in the topology

        :type feature: str
        :return: any
        """
        if feature == 'config_file':
            return self.config_file
        feat_map = self.get_topology_features()
        if feature in feat_map:
            return feat_map[feature]
        return None

    def print_features(self, logger=None):
        print_list = []
        for feat, val in self.get_topology_features().iteritems():
            print_list.append((str(feat), str(val)))
        if not logger:
            print("Supported features of this ptm:")
        else:
            logger.info("Supported features of this ptm:")
        for feat, val in print_list:
            if not logger:
                print(feat + ' = ' + str(val))
            else:
                logger.info(feat + ' = ' + str(val))

    def add_fixture(self, name, fixture):
        """
        Add a ServiceFixture to setup and tear down this scenario in
        addition to standard setup() and teardown() functions defined
        in scenario subclasses (most notably, this is useful when a
        certain batch of tests have specialized scenario needs that
        aren't suitable to create a hard dependency to the scenario
        subclass, such as virtual topology requirements, etc.).  The
        fixtures are added by name so they can be checked and accessed
        at a later time (or only set to be included once from many
        sources, etc.)
        :type name: str
        :type fixture: ServiceFixture
        """
        if fixture:
            self.fixtures[name] = fixture

    def fixture_setup(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: ServiceFixture"""
            fix.setup()

    def fixture_teardown(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: ServiceFixture"""
            fix.teardown()

    def get_fixture(self, name):
        if name in self.fixtures:
            return self.fixtures[name]
        raise exceptions.ObjectNotFoundException(
            'No fixture defined in scenario: ' + name)
