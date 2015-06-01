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

from NetworkObject import NetworkObject
from VirtualInterface import VirtualInterface

class VLAN(NetworkObject):
    def __init__(self, vlan_id, host):
        super(VLAN, self).__init__(vlan_id, host.get_cli())
        self.vlan_id = vlan_id
        self.interfaces = []
        """ :type: list[(VirtualInterface, IPDef)]"""

    def add_interface(self, interface, ip_list):
        self.interfaces.append((interface, ip_list))

    def print_config(self, indent=0):
        print ('    ' * indent) + 'ID: ' + str(self.vlan_id)
        print ('    ' * (indent + 1)) + 'Configured Hosts/Interfaces: '
        for ifaces in self.interfaces:
            print ('    ' * (indent + 2)) + 'Host: ' + ifaces[0].get_host_name()
            print ('    ' * (indent + 3)) + ifaces[0].get_interface_name() + \
                  ' on IPs: ' + ', '.join(str(ip) for ip in ifaces[1])

    def link_interfaces(self):
        for iface in self.interfaces:
            iface[0].link_vlan(self.vlan_id, iface[1])

    def unlink_interfaces(self):
        for iface in self.interfaces:
            iface[0].unlink_vlan(self.vlan_id)
