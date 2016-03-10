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

from zephyr.common.ip import IP
from zephyr.ptm.host.interface import Interface
from zephyr.ptm.host.virtual_interface import VirtualInterface


class Bridge(Interface):
    def __init__(self, name, host, mac=None, ip_addr=None, options=None):
        """
        A Linux bridge with linked interfaces.
        :type name: str
        :type host: Host Host to configure bridge upon
        :type mac: str
        :type ip_addr: list [IP]
        :type options: list[str]
        """
        super(Bridge, self).__init__(name=name, host=host, mac=mac,
                                     ip_addr=ip_addr, linked_bridge=None)
        self.options = options if options is not None else []
        self.linked_interfaces = {}
        """ :type: dict [str, Interface]"""

    def create(self):
        self.cli.cmd('brctl addbr ' + self.get_name())
        # Link all configured interfaces to this bridge
        # Set any configured options
        for i in self.options:
            # Spanning Tree Protocol
            if i == 'stp':
                self.cli.cmd('brctl stp ' + self.get_name() + ' on')

    def remove(self):
        if len(self.ip_list) > 0:
            for i in self.linked_interfaces.itervalues():
                # If this bridge has an IP, and the interface is a veth
                # device, remove any routes on the peer's host (far-end)
                # pointing to this bridge
                if i.state is Interface.UP and isinstance(i, VirtualInterface):
                    """ :type i: VirtualInterface"""
                    i.peer_interface.host.del_route(IP('0.0.0.0', '0'))
        # Remove the bridge (note, bridge interface must be DOWN for
        # removal to work)
        self.cli.cmd('brctl delbr ' + self.get_name())

    def link_interface(self, iface):
        """
        Link an interface to this bridge.
        :param iface: Interface Interface to link
        :return:
        """
        self.cli.cmd('brctl addif ' + self.get_name() + ' ' + iface.name)
        self.linked_interfaces[iface.name] = iface

    def unlink_interface(self, iface):
        """
        Unlink an interface to this bridge.
        :param iface: Interface Interface to unlink
        :return:
        """
        self.cli.cmd('brctl delif ' + self.get_name() + ' ' + iface.name)
        self.linked_interfaces.pop(iface.name)

    def print_config(self, indent=0):
        print(('    ' * indent) + self.name +
              (' with ip(s): ' + ', '.join(str(ip) for ip in self.ip_list)
               if len(self.ip_list) > 0
               else ''))
