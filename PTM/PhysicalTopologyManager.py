__author__ = 'micucci'
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

from RootHost import RootHost
from PhysicalTopologyConfig import PhysicalTopologyConfig
from Host import Host
from HypervisorHost import HypervisorHost

from common.Exceptions import *
from common.CLI import *
from common.LogManager import LogManager
from common.FileLocation import *

import logging
import json
import sys
import importlib
import datetime

HOST_CONTROL_CMD_NAME = 'ptm-host-ctl.py'
CONTROL_CMD_NAME = 'ptm-ctl.py'
PTM_LOG_FILE_NAME = 'ptm-output.log'

class PhysicalTopologyManager(object):
    """
    Manage physical topology for test.
    :type log_manager: LogManager
    :type logger: logging.logger
    :type console: logging.logger
    :type root_dir: str
    :type hosts_by_name: dict [str, Host]
    :type host_by_start_order: list [Host]
    :type hypervisors: dict[str, HypervisorHost]
    """
    def __init__(self, root_dir='.', log_manager=None):
        super(PhysicalTopologyManager, self).__init__()
        self.log_manager = log_manager if log_manager is not None else LogManager(root_dir="logs")
        """ :type: LogManager"""
        self.hosts_by_name = {}
        self.host_by_start_order = []
        self.hypervisors = {}
        self.root_dir = root_dir
        self.LOG = logging.getLogger('ptm-null-root')
        self.LOG.addHandler(logging.NullHandler())
        self.CONSOLE = logging.getLogger('ptm-null-console')
        self.CONSOLE.addHandler(logging.NullHandler())
        self.log_level = logging.INFO
        self.debug = False

    def configure_logging(self, log_name='ptm-root', log_file_name=PTM_LOG_FILE_NAME, debug=False):

        self.log_level = logging.DEBUG if debug is True else logging.INFO
        self.debug = True

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(file_name=log_file_name,
                                                       name=log_name + '-debug',
                                                       file_log_level=self.log_level,
                                                       stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(file_name=log_file_name,
                                                        name=log_name,
                                                        log_level=self.log_level)

        self.CONSOLE = self.log_manager.add_stdout_logger(name=log_name + '-console', log_level=logging.INFO)

        # Update all loggers for all configured hosts
        for host in self.hosts_by_name.itervalues():
            host.set_log_level(self.log_level)

    def configure(self, file_name='config/ptm-config.json', file_type='json'):
        """
        Configure the PTM with information from the given JSON file
        :type file_name: str
        :return:
        """
        self.LOG.debug('**PTM configuration started**')
        self.LOG.debug('Configuring PTM with file: ' + file_name)
        #TODO: Enable multiple config files to define roots across several Linux hosts
        config_obj = None
        with open(file_name, 'r') as f:
            if file_type == 'json':
                config_obj = json.load(f)
            else:
                raise InvallidConfigurationException('Could not open file of type: ' + file_type)

        self.LOG.debug('Read JSON, configure object=' + str(config_obj))
        ptc = PhysicalTopologyConfig.make_physical_topology(config_obj)

        # We need a root server to act as the "local host" with access to the base Linux OS
        if 'root' not in ptc.hosts or 'root' not in ptc.implementation:
            raise ObjectNotFoundException('Physical Topology must have one host and implementation for "root"')

        self.LOG.debug('Configuring PTM host setup')
        # Configure each host in the configuration with its name and bridge/interface
        # definitions
        for host_cfg in ptc.hosts.itervalues():

            if host_cfg.name not in ptc.implementation:
                raise ObjectNotFoundException('No implementation for host: ' + host_cfg.name)

            # Get the impl details and use that to instance a basic object
            impl_cfg = ptc.implementation[host_cfg.name]

            # Module name is the whole string, while class name is the last name after the last dot (.)
            mod_name = impl_cfg.impl
            class_name = impl_cfg.impl.split('.')[-1]

            self.LOG.debug('Configuring host: ' + host_cfg.name + ' with impl: ' + mod_name + "/" + class_name)
            module = importlib.import_module(mod_name)
            impl_class = getattr(module, class_name)

            h = impl_class(host_cfg.name, self)
            """ :type h: Host"""
            if self.debug is True:
                host_logger = self.log_manager.add_tee_logger(file_name=PTM_LOG_FILE_NAME,
                                                              name=h.name,
                                                              file_log_level=self.log_level,
                                                              stdout_log_level=self.log_level)
            else:
                host_logger = self.log_manager.add_file_logger(PTM_LOG_FILE_NAME,
                                                               name=h.name,
                                                               log_level=self.log_level)
            h.set_logger(host_logger)
            self.hosts_by_name[h.name] = h

            if h.is_hypervisor():
                self.hypervisors[h.name] = h
                self.LOG.debug('Adding host to hypervisor list:' + h.name)

            self.LOG.debug('Configuring individual host:' + h.name)
            # Now configure the host with the definition and impl configs
            h.config_from_ptc_def(host_cfg, impl_cfg)

        # After the hosts are all added and configured, we can cross-reference
        # any mention of hosts in the wiring config and build a map that links
        # near host/interface to a far host object and with its interface
        # definition.

        # The wire config looks like this:
        # {
        #   'host1': {
        #     'eth0': { host: 'hostz' interface: 'eth0' }
        #     'eth1': { host: 'hosty' interface: 'eth0' }
        #   }
        #  'host2': {
        #     'eth0': { host: 'hostx' interface: 'eth0' }
        #     ... and so on

        # This means we can give each host a map of interfaces to far host and interface
        #  objects:
        # {
        #   'eth0': { host: Host() for 'hostz' interface: Interface() for 'eth0' }
        #   'eth1': { host: Host() for 'hosty' interface: Interface() for 'eth0' }
        #   ... and so on
        # }
        #
        # This map can be used to wire hosts to each other

        for host in self.hosts_by_name.itervalues():

            self.LOG.debug('Connecting host based on wiring scheme:' + host.name)
            # If host has a map entry for wiring, configure the wiring map for that host
            # If not, then skip any wiring configuration.
            if host.name in ptc.wiring:
                for if_name, wire in ptc.wiring[host.name].iteritems():
                    if if_name not in host.interfaces:
                        raise ObjectNotFoundException('No near interface ' + if_name +
                                                      ' found for connection from host ' + host.name)

                    near_iface = host.interfaces[if_name]

                    if wire.host not in self.hosts_by_name:
                        raise ObjectNotFoundException('No far host ' + wire.host +
                                                      ' found for connection from host ' + host.name)
                    far_host = self.hosts_by_name[wire.host]

                    if wire.interface not in far_host.interfaces:
                        raise ObjectNotFoundException('No far interface ' + wire.interface +
                                                      ' found for connection from host ' + host.name)

                    far_iface = far_host.interfaces[wire.interface]

                    self.LOG.debug('Link found:' + host.name + '/' + near_iface.name + ' -> ' +
                                   far_host.name + '/' + far_iface.name)

                    host.link_interface(near_iface, far_host, far_iface)

        for name in ptc.host_start_order:
            self.LOG.debug('Adding host to start list: ' + name)
            if name not in self.hosts_by_name:
                raise ObjectNotFoundException('Cannot set start order: host ' + name + ' not found')
            self.host_by_start_order.append(self.hosts_by_name[name])
        self.LOG.debug('**PTM configuration finished**')

    def print_config(self, indent=0, logger=None):
        print 'Hosts (in start-order):'
        for h in self.host_by_start_order:
            h.print_config(indent + 1)

    def startup(self):
        """
        Startup the configured Midonet cluster, including creating, booting, initializing,
        and starting all hosts
        :return:
        """
        self.LOG.debug('**PTM starting up**')

        self.LOG.debug('PTM starting hosts')
        for h in self.host_by_start_order:
            self.LOG.debug('PTM creating host: ' + h.name)
            h.create()

        for h in self.host_by_start_order:
            self.LOG.debug('PTM booting host: ' + h.name)
            h.boot()

        self.LOG.debug('PTM starting host network')
        for h in self.host_by_start_order:
            self.LOG.debug('PTM starting networks on host: ' + h.name)
            h.net_up()

        for h in self.host_by_start_order:
            self.LOG.debug('PTM finalizing networks on host: ' + h.name)
            h.net_finalize()

        self.LOG.debug('PTM starting host applications')
        for h in self.host_by_start_order:
            self.LOG.debug('PTM preparing config files on host: ' + h.name)
            h.prepare_config()

        for h in self.host_by_start_order:
            self.LOG.debug('PTM starting apps on host: ' + h.name)
            start_process = self.unshare_control('start', h)
            stdout, stderr = start_process.communicate()
            start_process.poll()
            #if start_process.returncode != 0:
            self.LOG.debug("Host control process output: ")
            self.LOG.debug(stdout)
            self.LOG.debug("Host control process error output: ")
            self.LOG.debug(stderr)
            #
            # raise SubprocessFailedException('Host control start failed with: ' + str(start_process.returncode))
            h.wait_for_process_start()

        self.LOG.debug('**PTM startup finished**')

    def shutdown(self):
        """
        Shutdown the configured Midonet cluster by stopping, shutting down, and removing all
        hosts
        :return:
        """
        self.LOG.debug('**PTM shutting down**')
        for h in reversed(self.host_by_start_order):
            self.LOG.debug('PTM stopping apps on host: ' + h.name)
            stop_process = self.unshare_control('stop', h)
            stdout, stderr = stop_process.communicate()
            stop_process.poll()
            if stop_process.returncode != 0:
                self.LOG.debug("Host control process output: ")
                self.LOG.debug(stdout)
                self.LOG.debug("Host control process error output: ")
                self.LOG.debug(stderr)
            h.wait_for_process_stop()

        self.LOG.debug('PTM stopping networks')
        for h in reversed(self.host_by_start_order):
            self.LOG.debug('PTM bringing down network on host: ' + h.name)
            h.net_down()

        self.LOG.debug('PTM stopping hosts')
        for h in reversed(self.host_by_start_order):
            self.LOG.debug('PTM stopping host: ' + h.name)
            h.shutdown()

        for h in reversed(self.host_by_start_order):
            self.LOG.debug('PTM deleting host: ' + h.name)
            h.remove()
        self.LOG.debug('**PTM shutdown finished**')

    def unshare_control(self, command, host, arg_list=list()):
        host_cfg_str = json.dumps(host.create_host_cfg_map_for_process_control()).replace('"', '\\"')
        cmd = 'unshare --mount --uts -- /bin/bash -x -c -- "PYTHONPATH=' + self.root_dir + ' python ' + \
              self.root_dir + '/' + HOST_CONTROL_CMD_NAME + ' -c ' + command + " -j '" + \
              host_cfg_str + "' -l " + self.log_manager.root_dir + " " + ' '.join(arg_list) + '"'

        return LinuxCLI().cmd(cmd, blocking=False).process

    def ptm_host_control(self, host_cmd, host_json, arg_list):

        self.LOG.debug('Running command: ' + host_cmd)
        self.LOG.debug('Loading JSON: ' + host_json)

        cfg_map = json.loads(host_json)

        # Module name is the whole string, while class name is the last name after the last dot (.)
        mod_name = cfg_map['impl']
        class_name = mod_name.split('.')[-1]

        host_name = cfg_map['name']

        module = importlib.import_module(mod_name)
        impl_class = getattr(module, class_name)

        h = impl_class(host_name, None)
        """ :type: Host"""
        h.set_logger(self.LOG)
        h.config_host_for_process_control(cfg_map)
        h.prepare_environment()

        if host_cmd == 'start':
            h.control_start()
        elif host_cmd == 'stop':
            h.control_stop()
        else:
            fn_name = 'control_' + host_cmd
            fn = getattr(h, fn_name)
            if fn is not None:
                fn(*arg_list)
            else:
                raise ArgMismatchException('Command implementation function not found on host class: ' +
                                           class_name + '.' + fn_name)

        h.cleanup_environment()
