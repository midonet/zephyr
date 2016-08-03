# Copyright 2016 Midokura SARL
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

import logging
import uuid

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common.ip import IP
from zephyr.common.tcp_dump import TCPDump
from zephyr.common.tcp_sender import TCPSender
from zephyr.common import utils
from zephyr.common import zephyr_constants
from zephyr.vtm.underlay import underlay_host

ECHO_SERVER_TIMEOUT = 3


class DirectUnderlayHost(underlay_host.UnderlayHost):
    def __init__(self, name, unique_id=None, overlay=None,
                 vm_type='zephyr.vtm.underlay.ipnetns_vm.IPNetnsVM',
                 hypervisor=True, logger=None):
        super(DirectUnderlayHost, self).__init__(name)
        self.cli = cli.LinuxCLI()
        self.overlay = overlay
        self.echo_server_procs = {}
        self.packet_captures = []
        self.vm_type = vm_type
        self.vms = {}
        self.hypervisor = hypervisor
        self.unique_id = unique_id if unique_id else uuid.uuid4()
        if logger:
            self.LOG = logger
        else:
            self.LOG = logging.getLogger("host-" + self.name)
            self.LOG.addHandler(logging.NullHandler())
        self.main_ip = '127.0.0.1'
        self.dhcpcd_is_running = set()
        self.taps = {}

    def create_vm(self, name=None):
        if not self.hypervisor:
            raise exceptions.ArgMismatchException(
                "Cannot start VM on: " + self.name + ", not a hypervisor.")

        vm_class = utils.get_class_from_fqn(self.vm_type)
        if not vm_class:
            raise exceptions.ArgMismatchException(
                "No such VM Type available to load: " + self.vm_type)

        if name in self.vms:
            raise exceptions.ArgMismatchException(
                "VM already created: " + name)

        new_vm = vm_class(
            name=name,
            overlay=self.overlay,
            hypervisor=self,
            logger=self.LOG)

        self.vms[name] = new_vm
        return new_vm

    def setup_vm_network(self, ip_addr=None, gw_ip=None):
        raise exceptions.ArgMismatchException(
            "Error; plugin_iface operation only valid on a VM host")

    def request_ip_from_dhcp(self, iface='eth0', timeout=10):
        raise exceptions.ArgMismatchException(
            "Error; request_ip_from_dhcp operation only valid on a VM host")

    def stop_dhcp_client(self, iface):
        raise exceptions.ArgMismatchException(
            "Error; stop_dhcp_client operation only valid on a VM host")

    def start_sshd(self):
        self.execute('sshd -o PidFile=/run/sshd.' + self.name + '.pid')

    def plugin_port(self, iface, port_id, mac=None, vlans=None):
        raise exceptions.ArgMismatchException(
            "Error; plugin_iface operation only valid on a VM host")

    def unplug_port(self, port_id):
        raise exceptions.ArgMismatchException(
            "Error; unplug_iface operation only valid on a VM host")

    def create_tap_interface_for_vm(
            self, tap_iface_name,
            vm_host, vm_iface_name,
            vm_mac=None, vm_ip_list=None,
            vm_linked_bridge=None, vm_vlans=None):
        if not self.hypervisor:
            raise exceptions.ArgMismatchException(
                "Can only create a tap for a VM on a hypervisor host")

        peer_name = vm_host.name

        self.LOG.debug(
            "Creating TAP interface: " + tap_iface_name + " to connect to"
            " VM interface: " + vm_iface_name +
            " with MAC [" + (str(vm_mac if vm_mac else 'Auto')) + "]" +
            " and IP(s) " +
            (str(vm_ip_list) if vm_ip_list else 'discovered via DHCP') +
            (" and VLANS " +
             str(vm_vlans) if vm_vlans else ''))

        self.execute(
            'ip link add dev ' + tap_iface_name +
            ' type veth peer name ' + peer_name)

        self.execute(
            'ip link set dev ' + peer_name + ' netns ' +
            self.name + ' name ' + vm_iface_name)

        self.execute('ip link set dev ' + tap_iface_name + ' up')
        vm_host.execute('ip link set dev ' + vm_iface_name + ' up')

        self.cli.cmd(
            'ip link add dev ' + tap_iface_name +
            ' type veth peer name ' + tap_iface_name + '.p')

        if vm_host.name not in self.taps:
            self.taps[vm_host.name] = set()
        self.taps[vm_host.unique_id].add(tap_iface_name)

        self.LOG.debug("Creating tap interface on hypervisor [" +
                       str(self.name) +
                       "] with name [" + str(tap_iface_name) + "]")

    def remove_taps(self, vm_host):
        if vm_host.unique_id in self.taps:
            for tap in self.taps[vm_host.unique_id]:
                self.execute('ip link del dev ' + tap)

    def get_hypervisor_name(self):
        raise exceptions.ArgMismatchException(
            "Error; getting hypervisor operation only valid on a VM host")

    def fetch_file(self, file_name, **kwargs):
        self.cli.cat(file_name)

    def fetch_overlay_settings(self):
        return {}

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        """
        :type route_ip: IP
        :type gw_ip: IP
        :type dev: str
        :rtype:
        """
        if gw_ip is None:
            if dev is None:
                raise exceptions.ArgMismatchException(
                    'Must specify either next-hop GW or device to add a route')
            self.execute('ip route add ' + str(route_ip) + ' dev ' + str(dev))
        else:
            self.execute('ip route add ' + str(route_ip) + ' via ' + gw_ip.ip +
                         (' dev ' + str(dev) if dev else ''))

    def del_route(self, route_ip):
        self.execute('ip route del ' + str(route_ip.ip))

    def interface_down(self, iface):
        self.cli.cmd('ip link set dev ' + iface + ' down')

    def interface_up(self, iface):
        self.cli.cmd('ip link set dev ' + iface + ' up')

    def add_ip(self, iface_name, ip_addr):
        self.cli.cmd('ip addr add ' + str(ip_addr) + ' dev ' + iface_name)
        self.main_ip = ip_addr

    # noinspection PyUnresolvedReferences
    def get_ip(self, iface_name):
        return (
            self.cli.cmd(
                'ip addr show dev ' + iface_name +
                " | grep -w inet | awk '{print $2}' | sed 's/\/.*//g'")
            .stdout.strip().split('\n')[0])

    def request_ip(self, iface_name):
        return None

    def reset_default_route(self, ip_addr):
        pass

    def reboot(self):
        pass

    def restart_host(self):
        pass

    def do_start_echo_server(self, ip_addr='localhost',
                             port=zephyr_constants.DEFAULT_ECHO_PORT,
                             echo_data="pong", protocol='tcp'):
        pass

    def do_stop_echo_server(self, ip_addr='localhost',
                            port=zephyr_constants.DEFAULT_ECHO_PORT):
        return None

    def do_send_echo_request(self, dest_ip='localhost',
                             dest_port=zephyr_constants.DEFAULT_ECHO_PORT,
                             echo_request='ping',
                             protocol='tcp', timeout=10):
        out_str = ""
        return out_str

    # Specialized host-testing methods
    def send_custom_packet(self, iface, **kwargs):
        """
        Send a custom TCP packet from this host using args for
        TCPSender::send_packet()
        :type iface: str
        :type kwargs: dict[str, any]
        :rtype:
        """
        tcps = TCPSender()
        return tcps.send_packet(self.cli, interface=iface, **kwargs).stdout

    def send_arp_packet(self, iface, dest_ip, source_ip=None,
                        command='request',
                        source_mac=None, dest_mac=None,
                        packet_options=None, count=1):
        """
        Send [count] ARP packet(s) from this host with command as "request"
        or "reply".
        :type iface :str
        :type dest_ip: str
        :type source_ip: str
        :type command: str
        :type source_mac: str
        :type dest_mac: str
        :type packet_options: dict[str, str]
        :type count: int
        :rtype:
        """
        tcps = TCPSender()
        opt_map = {'command': command}
        if source_mac is not None:
            opt_map = {'smac': source_mac}
        if dest_mac is not None:
            opt_map = {'tmac': dest_mac}
        if source_ip is not None:
            opt_map = {'sip': source_ip}
        if dest_ip is not None:
            opt_map = {'tip': dest_ip}
        opt_map += packet_options
        return tcps.send_packet(self.cli, interface=iface, dest_ip=dest_ip,
                                packet_type='arp',
                                packet_options=opt_map, count=count).stdout

    def send_tcp_packet(self, iface, dest_ip,
                        source_port, dest_port, data=None,
                        packet_options=None, count=1):
        """
        Send [count] TCP packets from this Host using TCPSender::Send_packet()
        :type iface: str
        :type dest_ip: str
        :type source_port: int
        :type dest_port: int
        :type data: str
        :type packet_options: dict[str,str]
        :type count: int
        :rtype:
        """
        tcps = TCPSender()
        return tcps.send_packet(self.cli,
                                interface=iface,
                                dest_ip=dest_ip,
                                packet_type='tcp',
                                source_port=source_port,
                                dest_port=dest_port,
                                payload=data,
                                packet_options=packet_options,
                                count=count).stdout

    def do_ping(self, target_ip, iface=None, count=1, timeout=None):
        """
        Ping a target IP.  Can specify the interface to use and/or the number
        of pings to send.  Returns true if all pings succeeded, false
        otherwise.
        :param target_ip: str: target IP in CIDR format
        :param iface: str: Interface or IP to act as source
        :param count: int: Number of pings to send
        :param timeout: int: Timeout before packets is marked as failed
        :rtype: bool
        """
        iface_str = (('-I ' + iface) if iface is not None else '')
        timeout_str = (('-W ' + str(timeout) + ' ')
                       if timeout is not None
                       else '')
        return self.execute('ping -n ' + iface_str +
                            ' -c ' + str(count) + ' ' +
                            timeout_str +
                            target_ip).ret_code == 0

    def start_capture(self, interface, count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None, save_dump_file=False,
                      save_dump_filename=None):
        """
        Starts the capture of packets on the host's interface with
        pcap_filter tools (e.g. tcpdump). This will start a process
        in the background listening for packets on the given interface.
        The actual packets can be retrieved via the 'capture_packets'
        method.  Capturing can be halted with the 'stop_capture'
        method.  Only one capture can be running per interface at any
        one time.  Use the PcapRule objects to assemble a filter via
        standard pcap_filter rules. A callback function is available
        to be called when each packet is parsed.  It must take at least
        a single PCAPPacket parameter, and any number of optional
        arguments (passed through the callback_args parameter).  The
        packet capture will be dumped to a temporary file, which can
        be saved off to a permanent location, if desired.
        :param interface: str: Interface to capture on ('any' is
        also acceptable)
        :param count: int: Number of packets to capture, or '0' to
        capture until explicitly stopped (default)
        :param ptype: str: Type of packet to filter
        :param pfilter: PcapRule: Ruleset for packet filtering
        :param callback: callable: Optional callback function
        :param callback_args: list[T]: Arguments to optional callback
        function
        :param save_dump_file: bool: Optionally save the temporary
        packet capture file
        :param save_dump_filename: str: Filename to save temporary
        packet capture file
        :rtype:
        """
        tcpd = (self.packet_captures[interface]
                if interface in self.packet_captures
                else TCPDump())
        """ :type: TCPDump """

        self.LOG.debug('Starting tcpdump on host: ' + self.name)

        tcpd.start_capture(cli=self.cli, interface=interface, count=count,
                           packet_type=ptype, pcap_filter=pfilter,
                           callback=callback, callback_args=callback_args,
                           save_dump_file=save_dump_file,
                           save_dump_filename=save_dump_filename,
                           blocking=False)

        self.packet_captures[interface] = tcpd

    def capture_packets(self, interface, count=1, timeout=None):
        """
        Wait for and return a list of [count] received packets on the given
        interface. The optional timeout can be specified to bound the time
        waiting for the packets (an exception will be raised if the timeout
        is hit).
        :param interface: str: Interface on which to wait for packets
        :param count: int: Number of packets to wait for (0 means just
        return what is buffered)
        :param timeout: int: Upper bound on length of time to wait before
        exception is raised
        :rtype: list [PCAPPacket]
        """
        if interface not in self.packet_captures:
            raise exceptions.ObjectNotFoundException(
                'No packet capture is running or was run on host/interface' +
                self.name + '/' + interface)
        tcpd = self.packet_captures[interface]
        return tcpd.wait_for_packets(count, timeout)

    def stop_capture(self, interface):
        """
        Stop the capture of packets on the given interface.  Any
        remaining packets can be accessed through the 'capture_packets'
        method.
        :param interface: str: Interface to stop capture on
        :rtype:
        """
        if interface in self.packet_captures:
            tcpd = self.packet_captures[interface]
            tcpd.stop_capture()

    def flush_arp(self):
        """
        Flush the ARP table on this Host
        :rtype:
        """
        self.execute('ip neighbour flush all')

    def execute(self, cmd_line, timeout=None, blocking=True):
        return self.cli.cmd(cmd_line, timeout=timeout, blocking=blocking)

    def terminate(self):
        """
        Kill this Host.
        :rtype:
        """
        pass
