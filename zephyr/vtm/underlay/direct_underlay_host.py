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

import time
from zephyr.common.cli import LinuxCLI
from zephyr.common import echo_server
from zephyr.common import exceptions
from zephyr.common.ip import IP
from zephyr.common.tcp_dump import TCPDump
from zephyr.common.tcp_sender import TCPSender
from zephyr.common.utils import terminate_process
from zephyr.vtm.underlay import underlay_host

ECHO_SERVER_TIMEOUT = 3


class DirectUnderlayHost(underlay_host.UnderlayHost):
    def __init__(self, name):
        super(DirectUnderlayHost, self).__init__(name)
        self.cli = LinuxCLI()
        self.echo_server_procs = []
        self.packet_captures = []

    def create_vm(self, ip, mac, gw_ip, name):
        pass

    def fetch_file(self, file_name, **kwargs):
        self.cli.cat(file_name)

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        """
        :type route_ip: IP
        :type gw_ip: IP
        :type dev: str
        :return:
        """
        if gw_ip is None:
            if dev is None:
                raise exceptions.ArgMismatchException(
                    'Must specify either next-hop GW or device to add a route')
            self.cli.cmd('ip route add ' + str(route_ip) + ' dev ' + str(dev))
        else:
            self.cli.cmd('ip route add ' + str(route_ip) + ' via ' + gw_ip.ip +
                         (' dev ' + str(dev) if dev else ''))

    def del_route(self, route_ip):
        self.cli.cmd('ip route del ' + str(route_ip.ip))

    def create_interface(self, iface, mac=None, ip_list=None,
                         linked_bridge=None, vlans=None):
        pass

    def add_ip(self, iface_name, ip_addr):
        pass

    def reset_default_route(self, ip_addr):
        pass

    def reboot(self):
        pass

    def start_echo_server(self, ip_addr='localhost',
                          port=echo_server.DEFAULT_ECHO_PORT,
                          echo_data="echo-reply", protocol='tcp'):
        """
        Start an echo server listening on given ip/port (default to
        localhost:80) which returns the echo_data on any TCP
        connection made to the port.
        :param ip_addr: str
        :param port: int
        :param echo_data: str
        :param protocol: str
        :return: CommandStatus
        """
        if (port in self.echo_server_procs and
                self.echo_server_procs[port] is not None):
            self.stop_echo_server(ip_addr, port)
        proc_name = 'echo-server.py'
        self.LOG.debug('Starting echo server: ' + proc_name + ' on: ' +
                       ip_addr + ':' + str(port))
        cmd0 = [proc_name,
                '-i', ip_addr,
                '-p', str(port),
                '-d', echo_data,
                '-r', protocol]
        proc = self.cli.cmd_pipe(commands=[cmd0], blocking=False)
        timeout = time.time() + ECHO_SERVER_TIMEOUT

        conn_resp = ''
        while conn_resp != 'connect-test:' + echo_data:
            proc.process_array[0].poll()
            if proc.process_array[0].returncode is not None:
                out, err = proc.process.communicate()
                self.LOG.error('Error starting echo server: ' +
                               str(out) + '/' + str(err))
                raise exceptions.SubprocessFailedException(
                    'Error starting echo server: ' + str(out) + '/' +
                    str(err))
            if time.time() > timeout:
                raise exceptions.SubprocessTimeoutException(
                    'Echo server listener failed to bind to port '
                    'within timeout')
            conn_resp = self.send_echo_request(
                dest_ip=ip_addr, dest_port=port,
                echo_request='connect-test',
                protocol=protocol)

        self.echo_server_procs[port] = proc
        return proc

    def stop_echo_server(self, ip_addr='localhost',
                         port=echo_server.DEFAULT_ECHO_PORT):
        """
        Stop an echo server that has been started on given ip/port (defaults to
        localhost:80).  If echo service has not been started, do nothing.
        :param ip_addr: str
        :param port: int
        :return:
        """
        if (port in self.echo_server_procs and
                self.echo_server_procs[port] is not None):
            self.LOG.debug('Stopping echo server on: ' +
                           ip_addr + ':' + str(port))
            proc = self.echo_server_procs[port]
            proc.process_array[0].poll()
            terminate_process(proc.process, signal='TERM')

            timeout = time.time() + ECHO_SERVER_TIMEOUT
            pid_file = '/run/zephyr_echo_server.' + str(port) + '.pid'
            while self.cli.exists(pid_file):
                time.sleep(1)
                if time.time() > timeout:
                    terminate_process(proc.process, signal='KILL')
                    break
            self.cli.rm(pid_file)
            self.echo_server_procs[port] = None

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=echo_server.DEFAULT_ECHO_PORT,
                          echo_request='ping', source_ip=None,
                          protocol='tcp'):
        """
        Create a TCP connection to send specified request string to dest_ip
        on dest_port (defaults to localhost:80) and return the response.
        :param dest_ip: str
        :param dest_port: int
        :param echo_request: str
        :param source_ip: str
        :param protocol: str
        :return: str
        """
        self.LOG.debug('Sending echo command ' + echo_request + ' to: ' +
                       str(dest_ip) + ' ' + str(dest_port))
        echo_request += echo_server.TERMINATION_STRING
        cmd0 = ['echo', '-n', echo_request]
        cmd1 = ['nc']
        if protocol == 'udp':
            cmd1 += ['-u']
        if source_ip:
            cmd1 += ['-s', source_ip]
        cmd1 += ['-w', '20']
        cmd1 += [dest_ip, str(dest_port)]
        ret = self.cli.cmd_pipe(commands=[cmd0, cmd1])
        out_str = ret.stdout
        pos = out_str.find(echo_server.TERMINATION_STRING)
        if pos != -1:
            out_str = out_str[0:pos]
        self.LOG.debug('Received echo response: ' + out_str)
        return out_str

    # Specialized host-testing methods
    def send_custom_packet(self, iface, **kwargs):
        """
        Send a custom TCP packet from this host using args for
        TCPSender::send_packet()
        :type iface: str
        :type kwargs: dict[str, any]
        :return:
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
        :return:
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
        :return:
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

    def ping(self, target_ip, iface=None, count=1, timeout=None):
        """
        Ping a target IP.  Can specify the interface to use and/or the number
        of pings to send.  Returns true if all pings succeeded, false
        otherwise.
        :param target_ip: str: target IP in CIDR format
        :param iface: str: Interface or IP to act as source
        :param count: int: Number of pings to send
        :param timeout: int: Timeout before packets is marked as failed
        :return: bool
        """
        iface_str = (('-I ' + iface) if iface is not None else '')
        timeout_str = (('-W ' + str(timeout) + ' ')
                       if timeout is not None
                       else '')
        return self.cli.cmd('ping -n ' + iface_str +
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
        :return:
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
        :return: list [PCAPPacket]
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
        :return:
        """
        if interface in self.packet_captures:
            tcpd = self.packet_captures[interface]
            tcpd.stop_capture()

    def flush_arp(self):
        """
        Flush the ARP table on this Host
        :return:
        """
        self.cli.cmd('ip neighbour flush all')

    def execute(self, cmd_line, timeout=None, blocking=True):
        self.cli.cmd(cmd_line, timeout=timeout, blocking=blocking)

    def terminate(self):
        """
        Kill this Host.
        :return:
        """
        pass
