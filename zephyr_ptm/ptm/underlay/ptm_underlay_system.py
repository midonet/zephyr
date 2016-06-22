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

import os

from zephyr.common import exceptions
from zephyr.vtm.underlay import underlay_system
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm import physical_topology_manager
from zephyr_ptm.ptm.underlay import ptm_underlay_host


class PTMUnderlaySystem(underlay_system.UnderlaySystem):
    global_vm_id = 0

    def __init__(self, debug=False, logger=None):
        super(PTMUnderlaySystem, self).__init__(debug=debug, logger=logger)
        self.ptm = None
        self.root_dir = '.'
        self.ptm_log_file = 'ptm-out.log'

    def read_config(self, config_map):
        super(PTMUnderlaySystem, self).read_config(config_map)

        self.root_dir = config_map.get('root_dir', '.')
        self.ptm_log_file = config_map.get('ptm_log_file', 'ptm-out.log')

        if 'topology_config_file' not in config_map:
            raise exceptions.ArgMismatchException(
                "'topology_config_file' MUST be in PTM underlay config")

        topo_config = config_map['topology_config_file']
        self.ptm = physical_topology_manager.PhysicalTopologyManager(
            root_dir=self.root_dir,
            log_manager=self.log_manager)
        self.ptm.configure_logging(
            log_file_name=self.ptm_log_file,
            debug=self.debug)
        config_path = os.path.dirname(topo_config)
        config_file = os.path.basename(topo_config)
        self.ptm.configure(config_file=config_file,
                           config_dir=config_path)

        self.hosts = {
            name: ptm_underlay_host.PTMUnderlayHost(
                name=name,
                host_obj=host)
            for name, host in self.ptm.hosts_by_name.items()}

        for hv in self.ptm.hypervisors.keys():
            if hv in self.hosts:
                self.hypervisors[hv] = self.hosts[hv]

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param ip_addr: str IP Address to use for the VM (required)
        :param mac: str Ether Address to use for the VM (required)
        :param gw_ip: str GW IP to use for the VM (required)
        :param hv_host: str: Hypervisor to use, otherwise the
        least-loaded HV host is chosen.
        :param name: str: Name to use for the VM.  Otherwise one
        is generated.
        :return: Guest
        """
        self.LOG.debug(
            "Attempting to provision VM with IP: " + str(ip_addr) +
            (' on host: ' + hv_host if hv_host else '') +
            (' with name: ' + name if name else ''))
        start_hv_host = None
        """
        :type: zephyr_ptm.ptm.underlay.ptm_underlay_host.PTMUnderlayHost
        """

        if hv_host and hv_host not in self.hypervisors:
            raise exceptions.ObjectNotFoundException(
                'Requested host to start VM: ' + hv_host +
                ' not found')

        current_least_vm_count = -1
        if hv_host:
            start_hv_host = self.hypervisors[hv_host]
        else:
            for h, underlay_host in self.hypervisors.iteritems():
                host_obj = underlay_host.underlay_host_obj
                for hv_app in host_obj.applications_by_type[
                        application.APPLICATION_TYPE_HYPERVISOR]:
                    vm_count = hv_app.get_vm_count()
                    if (vm_count < current_least_vm_count or
                            current_least_vm_count == -1):
                        current_least_vm_count = vm_count
                        start_hv_host = underlay_host

        if not start_hv_host:
            raise exceptions.ObjectNotFoundException(
                'No suitable hypervisor service application '
                'found to launch VM')

        if name is not None:
            requested_vm_name = name
        else:
            requested_vm_name = 'vm_' + str(self.global_vm_id)
            self.global_vm_id += 1

        return start_hv_host.create_vm(
            ip_addr=ip_addr, mac=mac, gw_ip=gw_ip, name=requested_vm_name)

    def get_topology_feature(self, name):
        if name == "underlay_type":
            return "ptm"
        return self.ptm.get_topology_feature(name)
