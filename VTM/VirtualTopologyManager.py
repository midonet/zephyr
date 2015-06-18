__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import neutronclient.neutron.client

from common.Exceptions import *
from common.IP import IP

from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.ComputeHost import ComputeHost

from VTM.Guest import Guest


def create_neutron_client(api_version='2.0', endpoint_url='http://localhost:9696',
                          auth_strategy='noauth', **kwargs):
    return neutronclient.neutron.client.Client(api_version, endpoint_url=endpoint_url,
                                               auth_strategy=auth_strategy, **kwargs)

class VirtualTopologyManager(object):
    global_vm_id = 0

    def __init__(self,
                 physical_topology_manager,
                 client_api_impl=create_neutron_client()):

        self.client_api_impl = client_api_impl
        self.physical_topology_manager = physical_topology_manager
        """ :type: PhysicalTopologyManager"""

    def get_client(self):
        return self.client_api_impl

    def create_vm(self, ip=None, preferred_hv_host=None, preferred_name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param preferred_hv_host: str: Hypervisor to use, otherwise the least-loaded HV host is chosen.
        :param preferred_name: str: Name to use for the VM.  Otherwise one is generated.
        :return: Guest
        """
        if preferred_hv_host is None:
            # Pick the HV with the fewest running VMs
            least_busy_hv = None
            for hv in self.physical_topology_manager.hypervisors.itervalues():
                if least_busy_hv is None or least_busy_hv > hv.get_vm_count():
                    least_busy_hv = hv
            if least_busy_hv is None:
                raise ObjectNotFoundException('No suitable hypervisor found to launch VM')
            start_hv = least_busy_hv
        else:
            if preferred_hv_host not in self.physical_topology_manager.hypervisors:
                raise ObjectNotFoundException('Requested host to start VM: ' + preferred_hv_host + ' not found')
            start_hv = self.physical_topology_manager.hypervisors[preferred_hv_host]

        if preferred_name is not None:
            vm_name = preferred_name
        else:
            vm_name = 'vm_' + str(VirtualTopologyManager.global_vm_id)
            VirtualTopologyManager.global_vm_id += 1

        new_vm = start_hv.create_vm(vm_name)
        new_vm.create_interface('eth0', ip_list=[IP.make_ip(ip)])

        return Guest(new_vm)