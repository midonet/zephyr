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

from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.ComputeHost import ComputeHost

from common.Exceptions import *

class VirtualTopologyManager(object):
    global_vm_id = 0

    def __init__(self,
                 physical_topology_manager,
                 client_api_impl=neutronclient.neutron.client.Client,
                 endpoint_url='http://localhost:9696',
                 auth_strategy='noauth',
                 **kwargs):
        self.client_api_impl = client_api_impl(api_version='2.0',
                                               endpoint_url=endpoint_url,
                                               auth_strategy=auth_strategy,
                                               **kwargs)
        self.physical_topology_manager = physical_topology_manager

    def get_client(self):
        return self.client_api_impl

    def create_vm(self, preferred_hv_host=None, preferred_name=None):
        start_hv = None

        if preferred_hv_host is None:
            # Pick the HV with the fewest running VMs
            pass
        else:
            if preferred_hv_host not in self.physical_topology_manager:
                raise ObjectNotFoundException('Requested host to start VM: ' + preferred_hv_host + ' not found')
            start_hv = self.physical_topology_manager.hosts[preferred_hv_host]
            if not isinstance(start_hv, ComputeHost):
                raise ArgMismatchException('Requested host to start VM: ' + preferred_hv_host +
                                           ' is not a ComputeHost and cannot start VMs')
            """ :type start_hv: ComputeHost"""

            if preferred_name is not None:
                vm_name = preferred_name
            else:
                vm_name = 'vm_' + str(VirtualTopologyManager.global_vm_id)
                VirtualTopologyManager.global_vm_id += 1

            new_vm = start_hv.create_vm(vm_name)
            return new_vm