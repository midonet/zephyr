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

from PTM.host.Interface import Interface
from common.IP import IP


class VirtualInterface(Interface):
    def __init__(self, name, host, mac=None, ip_addr=list(), linked_bridge=None, vlans=None,
                 far_interface=None):
        """
        A virtual interface using the veth driver to create a pair of connected interfaces.
        One side of the pair is usually set to a far-end IP namespace, while the near end
        can be used in a Linux bridge, or directly as a separate interface.
        :type name: str
        :type host: Host Near host to start tunnel from
        :type mac: str
        :type ip_addr: list[IP]
        :type linked_bridge: Bridge Bridge to link to
        :type vlans: dict [str, list[IP]]
        :type far_interface: Interface
        """
        self.peer_name = name + '.p'
        super(VirtualInterface, self).__init__(name=name, host=host, mac=mac,
                                               ip_addr=ip_addr, linked_bridge=linked_bridge,
                                               vlans=vlans)

        # Set up an interface to represent the peer
        self.peer_interface = far_interface

    def create(self):
        """
        Link a veth peer to a far host and return the new interface
        :return: Interface The peer on the far host, configured and ready
        """
        self.cli.cmd('ip link add dev ' + self.get_name() + ' type veth peer name ' + self.peer_name)

        # Add interface to the linked bridge, if there is one
        if self.linked_bridge is not None:
            self.linked_bridge.link_interface(self)

        # Don't set the peer interface if it is null
        if self.peer_interface is None:
            return

        # move peer interface onto far host's namespace
        self.cli.cmd('ip link set dev ' + self.peer_name + ' netns ' +
                     self.peer_interface.host.name + ' name ' + self.peer_interface.name)

        # In the unlikely chance that the peer is also linked to a bridge, go ahead and link
        if self.peer_interface.linked_bridge is not None:
            self.peer_interface.linked_bridge.link_interface(self.peer_interface)

        # Now the peer can act like a separate, normal interface on the far host and
        # should be treated accordingly
        return self.peer_interface

    def remove(self):
        self.cli.cmd('ip link del dev ' + self.get_name())

    def config_addr(self):
        # Perform the normal address configuration, then set the peer's default route
        # to
        super(VirtualInterface, self).config_addr()

    def add_peer_route(self):
        # If linked bridge has an IP, and the interface is a veth device, add a route
        # on the peer's host (far-end) for all default traffic to come to the linked bridge
        if self.linked_bridge is not None and len(self.linked_bridge.ip_list) > 0:
            self.peer_interface.host.add_route(IP('0.0.0.0', '0'),
                                               self.linked_bridge.ip_list[0])

    def print_config(self, indent=0):
        print ('    ' * indent) + self.name + ' with peer: ' + \
              self.peer_interface.host.name + '/' + self.peer_interface.name
