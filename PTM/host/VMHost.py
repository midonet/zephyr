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

from PTM.host.IPNetNSHost import IPNetNSHost
from PTM.host.Interface import Interface
from PTM.application.HypervisorService import HypervisorService
from common.CLI import LinuxCLI
from common.Exceptions import *


class VMHost(IPNetNSHost):
    def __init__(self, name, ptm, hypervisor_host, hypervisor_app):
        super(VMHost, self).__init__(name, ptm)
        self.hypervisor_host = hypervisor_host
        """ :type: Host"""
        self.hypervisor_app = hypervisor_app
        """ :type: HypervisorService"""

    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def shutdown(self):
        super(VMHost, self).shutdown()
        for iface in self.interfaces.iterkeys():
            near_if_name = self.name + iface
            self.hypervisor_host.interfaces.pop(near_if_name, None)

    def create_interface(self, iface, mac=None, ip_list=None, linked_bridge=None, vlans=None):
        new_if = Interface(iface, self, mac, ip_list, linked_bridge, vlans)
        self.interfaces[iface] = new_if

        near_if_name = self.name + new_if.name
        self.LOG.debug("Creating VM interface: " + iface + " and veth peer on hypervisor [" +
                       str(self.hypervisor_host.name) + "] with name [" + str(near_if_name) + "] and IPs [" +
                       str([str(ip) for ip in ip_list]))
        self.hypervisor_host.link_interface(Interface(near_if_name, self.hypervisor_host), self, new_if)

        near_if = self.hypervisor_host.interfaces[near_if_name]
        """ :type: VirtualInterface"""
        near_if.create()
        near_if.up()
        near_if.config_addr()
        new_if.up()
        new_if.config_addr()
        new_if.start_vlans()

    def plugin_iface(self, iface, port_id, mac=None):
        if iface not in self.interfaces:
            raise ObjectNotFoundException('Cannot plug in interface: ' + iface + ' on VM ' +
                                          self.name + ' not found')
        self.LOG.debug('Connecting interface: ' + iface + ' to port ID: ' + port_id + ' with mac: ' +
                       'default' if mac is None else mac)
        self.hypervisor_app.connect_iface_to_port(self, self.interfaces[iface], port_id)
        if mac is not None:
            self.interfaces[iface].set_mac(mac)

    def unplug_iface(self, port_id):
        self.hypervisor_app.disconnect_port(port_id)

