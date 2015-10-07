__author__ = 'tomoe'
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


import subprocess
from PTM.VMHost import VMHost

class Guest(object):
    """
    A class to wrap a VM from the Physical Topology Manager
    """

    def __init__(self, vm_host):
        self.vm_host = vm_host
        """ :type: VMHost"""
        self.open_ports_by_id = set()
        """ :type: set[str]"""

    def plugin_vm(self, iface, port, mac=None):
        """ Links an interface on this VM to a virtual network port
            * bind interface to MidoNet with mm-ctl
            * set iface to the indicated mac address (if provided)
        :type iface: str
        :type port: str
        :type mac: str
        """
        self.vm_host.LOG.debug("Plugging in VM interface: " + iface + " to port: " + str(port))
        self.vm_host.plugin_iface(iface, port, mac)
        self.open_ports_by_id.add(port)

    def unplug_vm(self, port):
        """ Unlinks a port on this VM from the virtual network
        :type port: str
        """
        self.vm_host.LOG.debug("Unplugging VM port: " + str(port))
        self.vm_host.unplug_iface(port)
        self.open_ports_by_id.remove(port)

    def clear_arp(self):
        return self.vm_host.flush_arp()

    def send_arp_request(self, on_iface, ip):
        return self.vm_host.send_arp_packet(iface=on_iface, dest_ip=ip, command='request', count=1)

    def send_arp_reply(self, on_iface, src_mac, dest_mac, src_ip, dest_ip):
        return self.vm_host.send_arp_packet(iface=on_iface, dest_ip=dest_ip, source_ip=src_ip,
                                            source_mac=src_mac, dest_mac=dest_mac,
                                            command='reply', count=1)

    def send_packet(self, on_iface, **kwargs):
        return self.vm_host.send_custom_packet(iface=on_iface, **kwargs)

    def ping(self, on_iface, target_ip, count=3):
        return self.vm_host.ping(iface=on_iface, target_ip=target_ip, count=count)

    def execute(self, *args, **kwargs):
        result = self.vm_host.cli.cmd(*args, **kwargs)
        return result

    def terminate(self):
        for p in self.open_ports_by_id:
            self.vm_host.unplug_iface(p)
        self.open_ports_by_id.clear()
        self.vm_host.net_down()
        self.vm_host.shutdown()
        self.vm_host.remove()



