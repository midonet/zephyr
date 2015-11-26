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

from PTM.PTMObject import PTMObject
from common.IP import IP
from common.Exceptions import *

class Interface(PTMObject):

    # State
    DOWN = 0
    UP = 1

    def __init__(self, name, host, mac=None, ip_addr=None, linked_bridge=None, vlans=None):
        """
        Represents a faux-hardware link-layer interface on a host.  This base class
        cannot be used to create an interface on the OS, but it can be used for control
        of a real interface device post-creation (a veth peer, for example).
        :type name: str
        :type host: Host Near host
        :type mac: str
        :type ip_addr: list [IP]
        :type linked_bridge: Bridge Bridge to link to
        :type vlans: dict [str, list[IP]]
        """
        super(Interface, self).__init__(name, host.cli)
        self.state = Interface.DOWN
        self.host = host
        self.mac = mac
        self.ip_list = ip_addr if ip_addr is not None else []
        self.linked_bridge = linked_bridge
        self.vlans = vlans

    def create(self):
        pass

    def remove(self):
        pass

    def config_addr(self):
        if self.mac is not None:
            self.cli.cmd('ip link set dev ' + self.get_name() + ' address ' + self.mac)

        for ip in self.ip_list:
            self.cli.cmd('ip addr add ' + str(ip) + ' dev ' + self.get_name())

    def up(self):
        ret = self.cli.cmd('ip link set dev ' + self.get_name() + ' up')
        self.state = Interface.UP

    def down(self):
        self.cli.cmd('ip link set dev ' + self.get_name() + ' down')
        self.state = Interface.DOWN

    def set_mac(self, new_mac):
        self.mac = new_mac
        self.cli.cmd('ip link set dev ' + self.get_name() + ' address ' + new_mac)

    def add_ip(self, new_ip):
        """
        :type new_ip: IP
        """
        self.cli.cmd('ip addr add ' + str(new_ip) + ' dev ' + self.get_name())
        self.ip_list.append(new_ip)

    def start_vlans(self):
        if self.vlans is not None:
            for vlan_id, vlan_ips in self.vlans.iteritems():
                self.link_vlan(vlan_id, vlan_ips)

    def stop_vlans(self):
        if self.vlans is not None:
            for vlan_id in self.vlans.iterkeys():
                self.unlink_vlan(vlan_id)

    def link_vlan(self, vlan_id, ip_list):
        """
        :type vlan_id: int
        :type ip_list: list[IP]
        """
        vlan_iface = self.name + '.' + vlan_id
        self.cli.cmd('ip link add link ' + self.name + ' name ' +
                     vlan_iface + ' type vlan id ' + str(vlan_id))
        self.cli.cmd('ip link set dev ' + vlan_iface + ' up')
        for ip in ip_list:
            self.cli.cmd('ip addr add ' + str(ip) + ' dev ' + vlan_iface)

    def unlink_vlan(self, vlan_id):
        vlan_iface = self.name + '.' + str(vlan_id)
        self.cli.cmd('ip link set dev ' + vlan_iface + ' down')
        self.cli.cmd('ip link del ' + vlan_iface)

    def print_config(self, indent=0):
        print ('    ' * indent) + self.name + ' with ips: ' + ', '.join(str(ip) for ip in self.ip_list)
        if self.linked_bridge is not None:
            print ('    ' * (indent+1)) + 'Linked on bridge: ' + self.linked_bridge.name
        if self.vlans is not None and len(self.vlans) > 0:
            print ('    ' * (indent+1)) + '[VLANS]'
            for name, v in self.vlans.iteritems():
                print ('    ' * (indent+2)) + 'ID: ' + name
                print ('    ' * (indent+3)) + 'IPs: ' + ', '.join(str(ip) for ip in v)
