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
from common.TCPSender import TCPSender
from common.TCPDump import TCPDump
from common.LogManager import LogManager
from common.IP import IP
from common.CLI import LinuxCLI

from PTMObject import PTMObject
from VirtualInterface import VirtualInterface
from Interface import Interface
from Bridge import Bridge
from PhysicalTopologyConfig import *

import logging
import json

# TODO: Extrapolate the host access from the host operations
# So we can have IPNetNSHost and "VMSSHHost", etc. and also have
# CassandraHost, etc. which supports Cassandra functionality but using
# a flexible accessor so it can run on IPNetNS or VMSSH, etc. without
# having to do multiple inheritance.
# TODO: [PRIORITY] Furthermore, we should extrapolate all process control
# completely, as the boot and network characterization of a host
# is only superficially linked to the process and its attendant
# configuration which will be running on it.  We should really only
# have a small number of host types, with many processes that can
# run on any kind of host.  This will help resolve the above issue
# as well.
class Host(PTMObject):
    def __init__(self, name, cli=LinuxCLI(), host_create_func=None, host_remove_func=None):
        super(Host, self).__init__(name, cli)
        self.bridges = {}
        """ :type: dict[str, Bridge]"""
        self.interfaces = {}
        """ :type: dict[str, Interface]"""
        self.create_func = host_create_func
        """ :type: lambda"""
        self.remove_func = host_remove_func
        """ :type: lambda"""
        self.log_manager = None
        """ :type: LogManager"""
        self.logger = logging.getLogger()
        """ :type: logging.Logger"""
        self.console = logging.getLogger()
        """ :type: logging.Logger"""

    def do_extra_config_from_ptc_def(self, cfg, impl_cfg):
        """
        Derivations of Host can override this to do extra config after the main Host
        configuration.
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        """
        pass

    def config_from_ptc_def(self, cfg, impl_cfg):
        """
        Configure from the given Physical Topology Config definition (in this case, a HostDef), and
        the implementation-specific configuration which can contain specific arguments
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        :return:
        """
        bridges = cfg.bridges if cfg.bridges is not None else {}
        """ :type: dict [str, BridgeDef]"""
        interfaces = cfg.interfaces if cfg.interfaces is not None else {}
        """ :type: dict [str, InterfaceDef]"""
        self.name = cfg.name

        # Configure bridges now, but hold off on interfaces until we get to wiring
        for name, br in bridges.iteritems():
            b = Bridge(name, self, br.mac_address, br.ip_addresses, br.options)
            self.bridges[name] = b

        for iface in interfaces.itervalues():
            link_br = None
            if iface.linked_bridge is not None:
                if iface.linked_bridge not in self.bridges:
                    raise ObjectNotFoundException('Linked bridge ' + iface.linked_bridge +
                                                  ' on interface not found on host ' + self.name)

                link_br = self.bridges[iface.linked_bridge]

            # Set up an interface here, but it will be replaced by a virtual interface if
            # this host/interface is defined as a near-pair in a wiring config
            self.interfaces[iface.name] = Interface(iface.name, self, iface.mac_address,
                                                            iface.ip_addresses, link_br, iface.vlans)

        self.do_extra_config_from_ptc_def(cfg, impl_cfg)

    def create_host_cfg_map_for_process_control(self):
        """
        Returns a map representing this object in order to start/stop the host process.
        """
        cfg_map = {'name': self.name, 'impl': self.__module__}
        extra_map = self.do_extra_create_host_cfg_map_for_process_control()
        if extra_map is not None:
            cfg_map.update(extra_map)
        return cfg_map

    def do_extra_create_host_cfg_map_for_process_control(self):
        """
        Hosts should override this function to add extra map parameters for the
        specific host implementation to the given config map
        :return: dict
        """
        return None

    def config_host_for_process_control(self, cfg_map):
        """
        Configure the host to be ready to control its process
        :type cfg_map: dict
        :return:
        """
        return self.do_extra_config_host_for_process_control(cfg_map)

    def do_extra_config_host_for_process_control(self, cfg_map):
        """
        Hosts should override this function to configure itself with any extra
        parameters specific to the host implementation
        :type cfg_map: dict
        :return:
        """
        pass

    def link_interface(self, near_interface, far_host, far_interface):
        """
        Configure a link using a VirtualInterface between this host/interface pair and
        the far end host/interface pair.
        :type near_interface: Interface
        :type far_host: Host
        :type far_interface: Interface
        :return:
        """

        # Create the Virtual Interface
        new_if = VirtualInterface(name=near_interface.name, host=near_interface.host, mac=near_interface.mac,
                                  ip_addr=near_interface.ip_list, linked_bridge=near_interface.linked_bridge,
                                  vlans=near_interface.vlans, far_interface=far_interface)

        self.interfaces[new_if.name] = new_if

    def set_log_manager(self, log_manager):
        """
        Sets the log manager and makes a root logger for this host
        :type log_manager: LogManager
        :return:
        """
        self.log_manager = log_manager
        self.logger = log_manager.get_logger('ptm-debug')
        self.console = log_manager.get_logger('ptm-console')

    def create(self):
        if self.create_func is not None:
            self.create_func(self.name)

    def remove(self):
        if self.remove_func is not None:
            self.remove_func(self.name)

    def boot(self):
        # Create and bring up all bridges since they are local
        for bridge in self.bridges.values():
            bridge.create()
            bridge.config_addr()
            bridge.up()

        # Create all interfaces, but wait to bring them up
        for interface in self.interfaces.itervalues():
            interface.create()

        self.set_loopback()

    def net_up(self):
        # Configure and bring up all network 'devices'
        for interface in self.interfaces.itervalues():
            interface.up()
            interface.config_addr()
            interface.start_vlans()

    def net_finalize(self):
        # Special for VETH pairs, set the peer's default route to this host's
        # bridge if a) it is present and b) it has IP addresses
        for interface in self.interfaces.itervalues():
            if isinstance(interface, VirtualInterface):
                """ :type interface: VirtualInterface"""
                interface.add_peer_route()

    def net_down(self):
        for interface in self.interfaces.itervalues():
            interface.stop_vlans()
            interface.down()

        for bridge in self.bridges.itervalues():
            bridge.down()

    def shutdown(self):
        for interface in self.interfaces.itervalues():
            interface.remove()

        for bridge in self.bridges.itervalues():
            bridge.remove()

    def set_loopback(self, ip=IP('127.0.0.1', '8')):
        if not self.cli.grep_cmd('ip addr | grep lo | grep inet', str(ip)):
            self.cli.cmd('ip addr add ' + str(ip) + ' dev lo')
        self.cli.cmd('ip link set dev lo up')

    def add_route(self, route_ip, gw_ip):
        self.cli.cmd('ip route add ' + str(route_ip) + ' via ' + gw_ip.ip)

    def del_route(self, route_ip):
        self.cli.cmd('ip route del ' + str(route_ip.ip))

    def print_config(self, indent=0):
        print ('    ' * indent) + self.name + ": Impl class " + self.__class__.__name__
        if self.bridges is not None and len(self.bridges) > 0:
            print ('    ' * (indent+1)) + '[bridges]'
            for b in self.bridges.itervalues():
                b.print_config(indent + 2)
        if self.interfaces is not None and len(self.interfaces) > 0:
            print ('    ' * (indent+1)) + '[interfaces]'
            for i in self.interfaces.itervalues():
                i.print_config(indent + 2)

    def prepare_config(self):
        pass

    # By default, do nothing for process control
    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def control_start(self):
        pass

    def control_stop(self):
        pass

    def prepare_environment(self):
        pass

    def cleanup_environment(self):
        pass

    # Specialized host-testing methods
    def send_packet(self, iface, type, target_ip, options=None, count=1):
        tcps = TCPSender()
        return tcps.send_packet(self.cli, interface=iface,
                                    dest_ip=target_ip,
                                    packet_type=type,
                                    packet_options=options)

    def ping(self, iface, target_ip, count=3):
        return self.cli.cmd('ping -n -I ' + iface + ' -c ' + str(count) + ' ' + target_ip, return_status=True) == 0

    def flush_arp(self):
        self.cli.cmd('ip neighbour flush all')

    def wait_for_packet(self, iface, type, target_ip, options, count=1, timeout=0):
        tcpd = TCPDump()
        return None #tcpd.read_packet(iface, target)