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
from PhysicalTopologyConfig import BridgeDef
from PhysicalTopologyConfig import IPDef


class Bridge(Interface):
    def __init__(self, name, near_host, options=list(), ip_list=list(), mac='default'):
        """
        :type name: str
        :type near_host: Host
        :type options: list[str]
        :type ip_list: list[IPDef]
        :type mac: str
        """
        super(Bridge, self).__init__(name=name,
                                     near_host=near_host,
                                     linked_bridge=None,
                                     ip_list=ip_list,
                                     mac=mac)

        self.options = options

    def setup(self):
        self.cli.cmd('brctl addbr ' + self.get_name())
        for ip in self.ip_list:
            self.cli.cmd('ip addr add ' + str(ip) + ' dev ' + self.get_name())

    def cleanup(self):
        self.cli.cmd('brctl delbr ' + self.get_name())

    def up(self):
        self.cli.cmd('ip link set dev ' + self.get_name() + ' up')
        for i in self.options:
            if i == 'stp':
                self.cli.cmd('brctl stp ' + self.get_name() + ' on')

    def down(self):
        self.cli.cmd('ip link set dev ' + self.get_name() + ' down')

    def add_link_interface(self, iface):
        self.cli.cmd('brctl addif ' + self.get_name() + ' ' + iface)

    def del_link_interface(self, iface):
        self.cli.cmd('brctl delif ' + self.get_name() + ' ' + iface)
