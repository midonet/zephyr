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


class HypervisorService(object):
    """
    A contract API to follow if an object is claiming to be a viable hypervisor
    in the Physical Topology system.
    """
    def create_vm(self, name):
        pass

    def is_hypervisor(self):
        pass

    def get_vm(self, name):
        pass

    def get_vm_count(self):
        pass

    def connect_iface_to_port(self, vm_host, iface, port_id):
        pass

    def disconnect_port(self, port_id):
        pass
