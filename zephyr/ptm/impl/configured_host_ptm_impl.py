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

from zephyr.common.exceptions import ArgMismatchException
from zephyr.common.exceptions import InvallidConfigurationException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.ip import IP
from zephyr.common.utils import get_class_from_fqn
from zephyr.ptm.application.hypervisor_service import HypervisorService
from zephyr.ptm.impl.physical_topology_manager_impl import (
    PhysicalTopologyManagerImpl)
from zephyr.ptm.physical_topology_config import PhysicalTopologyConfig
from zephyr.ptm.ptm_constants import ZEPHYR_LOG_FILE_NAME


class ConfiguredHostPTMImpl(PhysicalTopologyManagerImpl):
    global_vm_id = 0

    def __init__(self, root_dir='.', log_manager=None):
        super(ConfiguredHostPTMImpl, self).__init__(root_dir, log_manager)
        self.hosts_by_name = {}
        """ :type: dict[str, Host]"""
        self.host_by_start_order = []
        """ :type: list[Host|list[Host]]"""
        self.hypervisors = {}
        """ :type: dict[str, list[HypervisorService|Application]]"""
        self.virtual_network_hosts = {}

    def configure_logging(self, log_name='ptm-root', debug=False,
                          log_file_name=ZEPHYR_LOG_FILE_NAME):
        super(ConfiguredHostPTMImpl, self).configure_logging(
            log_name, debug, log_file_name)

        # Update all loggers for all configured hosts
        for host in self.hosts_by_name.itervalues():
            host.set_log_level(self.log_level)

    def configure(self, config_file, file_type='json'):
        """
        IMPORTANT NOTE!!!  For Hosts and for Applications, the
        implementation class name in the [implementation] section
        MUST have the class's name be the same name as the last
        dotted-name in the module (the string after the last
        dot (.), without the .py extension)!

        :param config_file:
        :param file_type:
        :return:
        """
        self.LOG.debug('**ptm configuration started**')
        self.LOG.debug('Configuring ptm with file: ' + config_file)
        # TODO(micucci): Enable multiple config files to define roots
        # across several Linux hosts
        config_obj = None
        with open(config_file, 'r') as f:
            if file_type == 'json':
                config_obj = json.load(f)
            else:
                raise InvallidConfigurationException(
                    config_file, 'Could not open file of type: ' + file_type)

        self.LOG.debug('Read JSON, configure object=' + str(config_obj))
        ptc = PhysicalTopologyConfig.make_physical_topology(config_obj)

        # We need a root server to act as the "local host" with
        # access to the base Linux OS
        if 'root' not in ptc.hosts or 'root' not in ptc.implementation:
            raise ObjectNotFoundException(
                'Physical Topology must have one host and '
                'implementation for "root"')

        self.LOG.debug('Configuring ptm host setup')
        # Configure each host in the configuration with its name
        # and bridge/interface
        # definitions
        for host_cfg in ptc.hosts.itervalues():

            if host_cfg.name not in ptc.implementation:
                raise ObjectNotFoundException(
                    'No implementation for host: ' + host_cfg.name)

            # Get the impl details and use that to instance a basic object
            impl_cfg = ptc.implementation[host_cfg.name]

            self.LOG.debug('Configuring host: ' + host_cfg.name +
                           ' with impl: ' + impl_cfg.impl)
            h = get_class_from_fqn(impl_cfg.impl)(host_cfg.name, self)
            """ :type h: Host"""
            h.configure_logging(debug=self.debug)
            self.hosts_by_name[h.name] = h

            self.LOG.debug('Configuring individual host:' + h.name)
            # Now configure the host with the definition and impl configs
            h.config_from_ptc_def(host_cfg, impl_cfg)

            if h.is_virtual_network_host():
                self.virtual_network_hosts[h.name] = h
                self.LOG.debug('Adding host to VN host list:' + h.name)

            for a in h.applications:
                if isinstance(a, HypervisorService):
                    """ :type a: HypervisorService"""
                    if a.is_hypervisor():
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
                        raise ObjectNotFoundException(
                            'No near interface ' + if_name +
                            ' found for connection from host ' + host.name)

                    near_iface = host.interfaces[if_name]

                    if wire.host not in self.hosts_by_name:
                        raise ObjectNotFoundException(
                            'No far host ' + wire.host +
                            ' found for connection from host ' + host.name)
                    far_host = self.hosts_by_name[wire.host]

                    if wire.interface not in far_host.interfaces:
                        raise ObjectNotFoundException(
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
                        raise ObjectNotFoundException(
                            'Cannot set start order: host ' + host +
                            ' not found')
                    tier_list.append(self.hosts_by_name[host])
                self.host_by_start_order.append(tier_list)
                pass
            else:
                if name not in self.hosts_by_name:
                    raise ObjectNotFoundException(
                        'Cannot set start order: host ' + name +
                        ' not found')
                self.host_by_start_order.append([self.hosts_by_name[name]])
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

        self.LOG.debug('**ptm shutdown finished**')

    def create_vm(self, ip, mac=None, gw_ip=None,
                  requested_hv_host=None, requested_vm_name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param ip: str IP Address to use for the VM (required)
        :param mac: str Ether Address to use for the VM (required)
        :param gw_ip: str GW IP to use for the VM (required)
        :param requested_hv_host: str: Hypervisor to use, otherwise the
        least-loaded HV host is chosen.
        :param requested_vm_name: str: Name to use for the VM.  Otherwise one
        is generated.
        :return: Guest
        """
        self.LOG.debug("Provisioning VM with IP: " + str(ip) +
                       (' on host: ' + requested_hv_host
                        if requested_hv_host
                        else '') +
                       (' with name: ' + requested_vm_name
                        if requested_vm_name
                        else ''))
        start_hv_app = None
        start_hv_host = None

        if requested_hv_host and requested_hv_host not in self.hypervisors:
            raise ObjectNotFoundException(
                'Requested host to start VM: ' + requested_hv_host +
                ' not found')

        for hv_host, hv_app_list in (
                self.hypervisors.iteritems()
                if requested_hv_host is None
                else [(requested_hv_host,
                       self.hypervisors[requested_hv_host])]):
            for hv_app in hv_app_list:
                if (start_hv_app is None or
                        start_hv_app.get_vm_count() > hv_app.get_vm_count()):
                    start_hv_app = hv_app
                    start_hv_host = hv_host

        if not start_hv_host or not start_hv_app:
            raise ObjectNotFoundException(
                'No suitable hypervisor service application '
                'found to launch VM')

        if requested_vm_name is not None:
            requested_vm_name = requested_vm_name
        else:
            requested_vm_name = 'vm_' + str(ConfiguredHostPTMImpl.global_vm_id)
            ConfiguredHostPTMImpl.global_vm_id += 1

        self.LOG.debug("Starting VM with name: " + requested_vm_name +
                       " and IP: " + str(ip) + " on hypervisor host: " +
                       start_hv_host +
                       ' using hypervisor service application: ' +
                       start_hv_app.name)
        new_vm = start_hv_app.create_vm(requested_vm_name)
        """ :type: VMHost """

        real_ip = IP.make_ip(ip)
        new_vm.create_interface('eth0', ip_list=[real_ip], mac=mac)
        if gw_ip is None:
            # Figure out a default gw based on IP, usually
            # (IP & subnet_mask + 1)
            subnet_mask = [255, 255, 255, 255]
            if real_ip.subnet != "":
                smask = int(real_ip.subnet)
                subnet_mask = []

                current_mask = smask
                for i in range(0, 4):
                    if current_mask > 8:
                        subnet_mask.append(255)
                    else:
                        lastmask = 0
                        for j in range(0, current_mask):
                            lastmask += pow(2, 8 - (j + 1))
                        subnet_mask.append(lastmask)
                    current_mask -= 8

            split_ip = real_ip.ip.split(".")
            gw_ip_split = []
            for ip_part in split_ip:
                gw_ip_split.append(int(ip_part) &
                                   subnet_mask[len(gw_ip_split)])

            gw_ip_split[3] += 1
            gw_ip = '.'.join(map(lambda x: str(x), gw_ip_split))

        self.LOG.debug("Adding default route for VM: " + gw_ip)

        new_vm.add_route(gw_ip=IP.make_ip(gw_ip))

        return new_vm

    def ptm_host_app_control(self, app_cmd, host_json, app_json, arg_list):

        self.LOG.debug('Running app command: ' + app_cmd)
        self.LOG.debug('Loading JSON for host: ' + host_json)
        self.LOG.debug('Loading JSON for app: ' + app_json)

        host_cfg_map = json.loads(host_json)
        app_cfg_map = json.loads(app_json)

        host_name = host_cfg_map['name']

        host_impl_class = get_class_from_fqn(host_cfg_map['impl'])
        app_impl_class = get_class_from_fqn(app_cfg_map['class'])

        h = host_impl_class(host_name, self)
        """ :type: Host"""
        a = app_impl_class(h)
        """ :type: Application"""

        h.configure_logging(debug=False)
        a.configure_logging(debug=False)

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
                raise ArgMismatchException(
                    'Command implementation function not '
                    'found on app class: ' +
                    app_cfg_map['class'] + '.' + fn_name)

        a.cleanup_environment()
        self.LOG.debug("ptm-host-ctl finished")

    def get_topology_features(self):
        return {'compute_hosts': len(self.hypervisors),
                'edge_hosts': len([h for h in self.hosts_by_name.iterkeys()
                                   if h.startswith('edge')]),
                'host_names': [h for h in self.hosts_by_name.iterkeys()]}
