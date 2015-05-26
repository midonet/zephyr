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

from Interface import Interface


class VirtualInterface(Interface):
    def __init__(self, name, near_host, far_host, far_iface_name, linked_bridge=None,
                 ip_list=list(), mac='default', peer_ext='.p'):
        """
        :type name: str
        :type near_host: Host
        :type far_host: Host
        :type far_iface_name: str
        :type linked_bridge: Bridge
        :type ip_list: list[IPDef]
        :type mac: str
        :type peer_ext: str
        """
        super(VirtualInterface, self).__init__(name, near_host, linked_bridge, ip_list, mac)
        self.peer_name = self.name + peer_ext
        self.far_host = far_host
        self.far_iface_name = far_iface_name

    def setup(self):
        # add a veth-type interface with a peer
        self.cli.cmd('ip link add dev ' + self.name + ' type veth peer name ' + self.peer_name)
        # move peer iface onto far host's namespace
        self.cli.cmd('ip link set dev ' + self.peer_name + ' netns ' +
                           self.far_host.name + ' name ' + self.far_iface_name)
        # add ips
        for ip in self.ip_list:
            self.far_host.cli.cmd('ip addr add ' + ip + ' dev ' + self.far_iface_name)

    def up(self):
        # Set main iface up
        super(VirtualInterface, self).up()
        # Set peer iface up on far host's namespace
        self.far_host.cli.cmd('ip link set dev ' + self.far_iface_name + ' up')
        
    def down(self):
        super(VirtualInterface, self).down()
        self.far_host.cli.cmd('ip link set dev ' + self.far_iface_name + ' down')

    def add_peer_route(self, route_ip, gw_ip):
        self.far_host.cli.cmd('ip route add ' + route_ip + ' via ' + gw_ip.ip_address)

    def del_peer_route(self, route_ip):
        self.far_host.cli.cmd('ip route del ' + route_ip)

    def link_vlan(self, vlan_id, ip_list):
        vlan_iface = self.far_iface_name + '.' + str(vlan_id)
        self.far_host.cli.cmd('ip link add link ' + self.far_iface_name +
                           ' name ' + vlan_iface + ' type vlan id ' + str(vlan_id))
        self.far_host.cli.cmd('ip link set dev ' + vlan_iface + ' up')
        for ip in ip_list:
            self.far_host.cli.cmd('ip addr add ' + ip + ' dev ' + vlan_iface)

    def unlink_vlan(self, vlan_id):
        vlan_iface = self.far_iface_name + '.' + str(vlan_id)
        self.far_host.cli.cmd('ip link set dev ' + vlan_iface + ' down')
        self.far_host.cli.cmd('ip link del ' + vlan_iface)

    def get_far_host(self):
        return self.far_host

    def get_host_name(self):
        return self.far_host.name

    def get_interface_name(self):
        return self.far_iface_name

    def print_config(self, indent=0):
        link = ' linked on bridge ' + self.linked_bridge.name + ', ' if self.linked_bridge is not None else ' '
        print ('    ' * indent) + self.name + link + 'peered as ' + self.far_host.name + \
               '/' + self.far_iface_name + ' with ips: ' + ', '.join(str(ip) for ip in self.ip_list)
