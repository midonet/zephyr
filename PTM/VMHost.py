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

from NetNSHost import NetNSHost
from Interface import Interface

from common.Exceptions import *

class VMHost(NetNSHost):
    def __init__(self, name, ptm, hyper_visor):
        super(VMHost, self).__init__(name, ptm)
        self.hyper_visor = hyper_visor
        """ :type: ComputeHost Hypervisor"""

    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def create_interface(self, iface, mac=None, ip_list=None, linked_bridge=None, vlans=None):
        new_if = Interface(iface, self, mac, ip_list, linked_bridge, vlans)
        self.interfaces[iface] = new_if
        self.hyper_visor.create_interface_for_vm(self, new_if)
        new_if.up()
        new_if.config_addr()
        new_if.start_vlans()

    def plugin_iface(self, iface, port_id, mac=None):
        if iface not in self.interfaces:
            raise ObjectNotFoundException('Cannot plug in interface: ' + iface + ' on VM ' +
                                          self.name + ' not found')
        self.LOG.debug('Connecting interface: ' + iface + ' to port ID: ' + port_id + ' with mac: ' +
                       'default' if mac is None else mac)
        self.hyper_visor.connect_iface_to_port(self, self.interfaces[iface], port_id)
        if mac is not None:
            self.interfaces[iface].set_mac(mac)

    def unplug_iface(self, port_id):
        self.hyper_visor.disconnect_port(port_id)

