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
from PhysicalTopologyConfig import IPDef


class Interface(NetworkObject):
    def __init__(self, name, near_host, linked_bridge=None, ip_list=list(), mac='default'):
        """
        :type name: str
        :type near_host: Host
        :type linked_bridge: Bridge
        :type ip_list: list[IPDef]
        :type mac: str
        """

        super(Interface, self).__init__(name, near_host.cli)
        self.near_host = near_host
        self.linked_bridge = linked_bridge
        self.ip_list = ip_list
        self.mac = mac

    def add(self):
        self.cli.cmd('ip link add dev ' + self.get_name())

        if self.mac != 'default':
            self.cli.cmd('ip link set dev ' + self.get_name() + ' address ' + self.mac)

        for ip in self.ip_list:
            self.cli.cmd('ip addr add ' + str(ip) + ' dev ' + self.get_name())

    def delete(self):
        self.cli.cmd('ip link del dev ' + self.get_name())

    def up(self):
        self.cli.cmd('ip link set dev ' + self.get_name() + ' up')

    def down(self):
        self.cli.cmd('ip link set dev ' + self.get_name() + ' down')

    def change_mac(self, new_mac):
        self.mac = new_mac
        self.cli.cmd('ip link set dev ' + self.get_name() + ' address ' + new_mac)

    def add_ip(self, new_ip):
        """
        :type new_ip: IPDef
        """
        self.ip_list.append(new_ip)
        self.cli.cmd('ip addr add ' + str(new_ip) + ' dev ' + self.get_name())

    def link_vlan(self, vlan_id, ip_list):
        """
        :type vlan_id: int
        :type ip_list: list[IPDef]
        """
        vlan_iface = self.name + '.' + str(vlan_id)
        self.cli.cmd('ip link add link ' + self.name +
                           ' name ' + vlan_iface + ' type vlan id ' + str(vlan_id))
        self.cli.cmd('ip link set dev ' + vlan_iface + ' up')
        for ip in ip_list:
            self.cli.cmd('ip addr add ' + str(ip) + ' dev ' + vlan_iface)

    def add_route(self, route_ip, gw_ip):
        self.cli.cmd('ip route add ' + str(route_ip) + ' via ' + gw_ip.ip_address)

    def del_route(self, route_ip):
        self.cli.cmd('ip route del ' + str(route_ip))

    def get_host_name(self):
        return self.near_host.get_name()

    def get_interface_name(self):
        return self.name

    def get_near_host(self):
        return self.near_host

    def print_config(self, indent=0):
        link = ' linked on bridge: ' + self.linked_bridge.name if self.linked_bridge is not None else ''
        print ('    ' * indent) + self.name + ' with ips: ' + ', '.join(str(ip) for ip in self.ip_list)
