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

from common.TCPSender import TCPSender
from common.TCPDump import *

from VirtualTopologyConfig import VirtualTopologyConfig
from Port import Port
from PTM.VMHost import VMHost

class Guest(object):
    """
    A class to wrap a VM from the Physical Topology Manager
    """

    def __init__(self, vm_host):
        self.vm_host = vm_host
        """ :type: VMHost"""
        self.open_ports_by_id = {}
        """ :type: dict[str, Port]"""

    def plugin_vm(self, iface, port):
        """ Links an interface on this VM to a virtual network port
            * bind interface to MidoNet with mm-ctl
        :type iface: str
        :type port: Port
        """

        self.vm_host.plugin_iface(iface, port.id)
        self.open_ports_by_id[port.id] = port

    def unplug_vm(self, port):
        """ Unlinks a port on this VM from the virtual network
        :type port: Port to unlink
        """
        self.vm_host.unplug_iface(port.id)
        self.open_ports_by_id.pop(port.id)

    def clear_arp(self):
        return self.vm_host.flush_arp()

    def send_arp_request(self, on_iface, ip):
        return self.vm_host.send_packet(on_iface,
                                        type='arp',
                                        options={'command': 'request'},
                                        target_ip=ip,
                                        count=1)

    def send_arp_reply(self, on_iface, src_mac, target_mac, src_ip, target_ip):
        return self.vm_host.send_packet(iface=on_iface,
                                        type='arp',
                                        target_ip=target_ip,
                                        options={'command': 'reply',
                                                 'smac': src_mac,
                                                 'tmac': target_mac,
                                                 'sip': src_ip,
                                                 'tip': target_ip},
                                        count=1)

    def send_packet(self, on_iface, target_ip, type, options, count):
        return self.vm_host.send_packet(iface=on_iface,
                                        type=type,
                                        target_ip=target_ip,
                                        options=options,
                                        count=count)

    def send_ping(self, on_iface, target_ip, count=3):
        return self.vm_host.ping(iface=on_iface, target_ip=target_ip, count=count)

    def execute(self, *args, **kwargs):
        result = self.vm_host.cli.cmd(*args, **kwargs)
        return result




