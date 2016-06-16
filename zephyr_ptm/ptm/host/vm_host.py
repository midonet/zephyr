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

from zephyr_ptm.ptm.host.interface import Interface
from zephyr_ptm.ptm.host.ip_netns_host import IPNetNSHost


class VMHost(IPNetNSHost):
    def __init__(self, name, ptm, hypervisor_host):
        super(VMHost, self).__init__(name, ptm)
        self.hypervisor_host = hypervisor_host

    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def shutdown(self):
        super(VMHost, self).shutdown()
        for iface in self.interfaces.iterkeys():
            near_if_name = self.name + iface
            old_tap_iface = self.hypervisor_host.interfaces.pop(
                near_if_name, None)
            """ :type: PTM.host.VirtualInterface.VirtualInterface """
            old_tap_iface.remove()

    def create_interface(self, iface, mac=None, ip_list=None,
                         linked_bridge=None, vlans=None):
        new_if = Interface(iface, self, mac, ip_list, linked_bridge, vlans)
        self.interfaces[iface] = new_if

        near_if_name = self.name + new_if.name
        self.LOG.debug("Creating VM interface: " + iface +
                       " and veth peer on hypervisor [" +
                       str(self.hypervisor_host.name) +
                       "] with name [" + str(near_if_name) + "] and IPs [" +
                       str([str(ip) for ip in ip_list]))
        self.hypervisor_host.link_interface(
            Interface(near_if_name, self.hypervisor_host), self, new_if)

        near_if = self.hypervisor_host.interfaces[near_if_name]
        """ :type: VirtualInterface"""
        near_if.create()
        near_if.up()
        near_if.config_addr()
        new_if.up()
        new_if.config_addr()
        new_if.start_vlans()
