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

from common.Exceptions import *
from NetworkObject import NetworkObject
from VirtualInterface import VirtualInterface
from Bridge import Bridge
from PhysicalTopologyConfig import *


class Host(NetworkObject):
    def __init__(self, name, cli, host_create_func, host_remove_func, root_host):
        super(Host, self).__init__(name, cli)
        self.bridges = {}
        """ :type: dict[str, Bridge]"""
        self.interfaces_for_host = {}
        """ :type: dict[str, dict[str, VirtualInterface]]"""
        self.hwinterfaces = {}
        """ :type: dict[str, VirtualInterface]"""
        self.create_func = host_create_func
        """ :type: lambda"""
        self.remove_func = host_remove_func
        """ :type: lambda"""
        self.root_host = root_host
        """ :type: Host"""

    def setup(self):
        self.create_func(self.name)

        for bridge in self.bridges.values():
            bridge.setup()
            bridge.up()

        for iface in self.hwinterfaces.itervalues():
            iface.setup()
            iface.up()

        self.set_loopback()

    def get_bridge(self, name):
        if name not in self.bridges:
            return None
        return self.bridges[name]

    def setup_host_interfaces(self, host):
        for interface in self.get_interfaces_for_host(host.get_name()).values():
            interface.setup()
            interface.up()
            if interface.linked_bridge is not None:
                br = self.root_host.get_bridge(interface.linked_bridge)
                br.add_link_interface(interface.get_name())
                if len(br.ip_list) is not 0:
                    interface.add_peer_route(IPDef('0.0.0.0', '0'), br.ip_list[0])

    def cleanup(self):
        for bridge in self.bridges.itervalues():
            bridge.down()
            bridge.cleanup()

        for interface in self.hwinterfaces.itervalues():
            interface.down()
            interface.cleanup()

        self.remove_func(self.name)

    def cleanup_interfaces(self, host):
        for interface in self.get_interfaces_for_host(host.get_name()).values():
            interface.down()
            interface.cleanup()

    def set_loopback(self, ip=IPDef('127.0.0.1', '8')):
        self.cli.cmd('ip addr add ' + str(ip) + ' dev lo')
        self.cli.cmd('ip link set dev lo up')

    def add_hwinterface(self, far_host, far_iface_name, linked_bridge, ip_list, mac='default'):
        """
        Add an interface to this host that tunnels to a far host, but is started and
        stopped normally when this host is started and stopped.
        :type far_host: Host
        :type far_iface_name: str
        :type linked_bridge: Bridge
        :type ip_list: list[IPDef]
        :type mac: str
        :return: VirtualInterface
        """
        if far_host is None:
            raise ArgMismatchException('Adding a virtual interface requires a far_host to tunnel to')
        if_name = 'v' + far_host.name + far_iface_name
        new_if = VirtualInterface(if_name, self, far_host, far_iface_name, linked_bridge, ip_list, mac, '.p')

        self.hwinterfaces[if_name] = new_if
        return new_if

    def add_virt_interface(self, far_host, far_iface_name, linked_bridge, ip_list, mac='default'):
        """
        Add an interface to this host that tunnels to a far host and is started/stopped
        via separate function calls, NOT when this host is started/stopped.

        :type far_host: Host
        :type far_iface_name: str
        :type linked_bridge: Bridge
        :type ip_list: list[IPDef]
        :type mac: str
        :return: VirtualInterface
        """
        if far_host is None:
            raise ArgMismatchException('Adding a virtual interface requires a far_host to tunnel to')

        if_name = 'v' + far_host.name + far_iface_name

        new_if = VirtualInterface(if_name, self, far_host, far_iface_name, linked_bridge, ip_list, mac, '.p')
        if far_host.get_name() not in self.interfaces_for_host:
            self.interfaces_for_host[far_host.get_name()] = {}
        self.interfaces_for_host[far_host.get_name()][far_iface_name] = new_if
        return new_if

    def get_interfaces_for_host(self, far_host):
        if far_host not in self.interfaces_for_host:
            raise ObjectNotFoundException(far_host)
        return self.interfaces_for_host[far_host]

    def print_config(self, indent=0):
        print ('    ' * indent) + self.name

    def start(self):
        pass

    def stop(self):
        pass

    def control_start(self, *args):
        pass

    def control_stop(self, *args):
        pass

    def mount_shares(self):
        pass

    def unmount_shared(self):
        pass

    def connect_iface_to_port(self, vm_host, iface, port_id):
        if vm_host not in self.interfaces_for_host:
            raise HostNotFoundException(vm_host)

        if iface not in self.interfaces_for_host[vm_host]:
            raise ObjectNotFoundException('interface ' + iface + ' on host ' + vm_host)

        near_iface = self.interfaces_for_host[vm_host][iface].name
        self.cli.cmd('mm-ctl --bind-port ' + port_id + ' ' + near_iface)

    def disconnect_port(self, port_id):
        self.cli.cmd('mm-ctl --unbind-port ' + port_id)

    def send_arp_request(self, iface, ip):
        return self.cli.send_packet(iface,
                                    pkt_type='arp',
                                    pkt_cmd='request',
                                    pkt_opt={'targetip': ip})

    def send_arp_reply(self, iface, src_mac, target_mac, src_ip, target_ip):
        return self.cli.send_packet(iface,
                                    pkt_type='arp',
                                    pkt_cmd='reply',
                                    pkt_opt={'smac': src_mac,
                                             'tmac': target_mac,
                                             'sip': src_ip,
                                             'tip': target_ip})

    def send_packet(self, iface, type, target_ip, options=None, count=1):
        return self.cli.send_packet(iface,
                                    target_ip=target_ip,
                                    pkt_type=type,
                                    pkt_cmd='request',
                                    pkt_opt=options)

    def flush_arp(self):
        self.cli.cmd('ip neighbour flush all')

    def wait_for_packet(self, iface, type, target_ip, options, count=1, timeout=0):
        return self.cli.sniff_packet(iface,
                                     target)