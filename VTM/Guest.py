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


import time

from common.Exceptions import *
from common.CLI import CommandStatus
from common.EchoServer import EchoServer, DEFAULT_ECHO_PORT
from common.Utils import terminate_process


PACKET_CAPTURE_TIMEOUT = 10
ECHO_SERVER_TIMEOUT = 3

class Guest(object):
    """
    A class to wrap a VM from the Physical Topology Manager
    """

    def __init__(self, vm_host):
        self.vm_host = vm_host
        """ :type: VMHost"""
        self.open_ports_by_id = set()
        """ :type: set[str]"""
        self.echo_server_procs = {}
        """ :type: dict[int, CommandStatus]"""

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

    def send_packet(self, on_iface='eth0', **kwargs):
        return self.vm_host.send_custom_packet(iface=on_iface, **kwargs)

    def send_tcp_packet(self, on_iface='eth0', data=None,
                        dest_ip=None,
                        source_port=None, dest_port=None,
                        packet_options=None, count=None):
        return self.vm_host.send_tcp_packet(iface=on_iface, dest_ip=dest_ip,
                                            source_port=source_port, dest_port=dest_port,
                                            data=data, packet_options=packet_options, count=count)

    def start_capture(self, on_iface='eth0',
                      count=0, type='', filter=None,
                      callback=None, callback_args=None,
                      save_dump_file=False, save_dump_filename=None):
        """
        :param interface: str: Interface to capture on ('any' is also acceptable)
        :param count: int: Number of packets to capture, or '0' to capture until explicitly stopped (default)
        :param type: str: Type of packet to filter
        :param filter: PCAP_Rule: Ruleset for packet filtering
        :param callback: callable: Optional callback function
        :param callback_args: list[T]: Arguments to optional callback function
        :param save_dump_file: bool: Optionally save the temporary packet capture file
        :param save_dump_filename: str: Filename to save temporary packet capture file
        """
        self.vm_host.start_capture(interface=on_iface, count=count, type=type, filter=filter,
                                   callback=callback, callback_args=callback_args,
                                   save_dump_file=save_dump_file, save_dump_filename=save_dump_filename)

    def capture_packets(self, on_iface='eth0', count=1, timeout=PACKET_CAPTURE_TIMEOUT):
        """
        Capture (count) number of packets that have come into the given interface on an
        running capture (raises ObjectNotFoundException if capture isn't running already),
        or wait (timeout) seconds for all the packets to arrive.  Returns the packet list
        and throws a SubprocessTimeoutException if the packets do not all arrive in time.
        :param on_iface: str
        :param count: int
        :param timeout: int
        :return: list[PCAPPacket]
        """
        return self.vm_host.capture_packets(interface=on_iface, count=count, timeout=timeout)

    def stop_capture(self, on_iface='eth0'):
        """
        Stop an already running capture, do nothing if capture is not running on interface.
        :param on_iface: str
        """
        self.vm_host.stop_capture(interface=on_iface)

    def ping(self, target_ip, on_iface='eth0', count=3):
        """
        Ping the target_ip on given interface and return true if the ping succeeds,
        false otherwise.
        :param target_ip: str
        :param on_iface: str
        :param count: int
        :return: bool
        """
        return self.vm_host.ping(target_ip=target_ip, iface=on_iface, count=count)

    def start_echo_server(self, ip='localhost', port=DEFAULT_ECHO_PORT, echo_data="echo-reply"):
        """
        Start an echo server listening on given ip/port (default to localhost:80)
        which returns the echo_data on any TCP connection made to the port.
        :param ip: str
        :param port: int
        :param echo_data: str
        :return: CommandStatus
        """
        if port in self.echo_server_procs and self.echo_server_procs[port] is not None:
            self.stop_echo_server(ip, port)
        proc_name = self.vm_host.ptm.root_dir + '/echo-server.py'
        self.vm_host.LOG.debug('Starting echo server: ' + proc_name + ' on: ' + ip + ':' + str(port))
        cmd0 = [proc_name, '-i', ip, '-p', str(port), '-d', echo_data]
        proc = self.vm_host.cli.cmd_pipe(commands=[cmd0], blocking=False)
        timeout = time.time() + ECHO_SERVER_TIMEOUT

        conn_resp = ''
        while conn_resp != 'connect-test:' + echo_data:
            proc.process_array[0].poll()
            if proc.process_array[0].returncode is not None:
                out, err = proc.process.communicate()
                self.vm_host.LOG.error('Error starting echo server: ' + str(out) + '/' + str(err))
                raise SubprocessFailedException('Error starting echo server: ' + str(out) + '/' + str(err))
            if time.time() > timeout:
                raise SubprocessTimeoutException('Echo server listener failed to bind to port within timeout')
            conn_resp = self.send_echo_request(dest_ip=ip, dest_port=port, echo_request='connect-test')

        self.echo_server_procs[port] = proc
        return proc

    def stop_echo_server(self, ip='localhost', port=DEFAULT_ECHO_PORT):
        """
        Stop an echo server that has been started on given ip/port (defaults to
        localhost:80).  If echo service has not been started, do nothing.
        :param port: int
        :return:
        """
        if port in self.echo_server_procs and self.echo_server_procs[port] is not None:
            self.vm_host.LOG.debug('Stopping echo server on: ' + ip + ':' + str(port))
            proc = self.echo_server_procs[port]
            proc.process_array[0].poll()
            terminate_process(proc.process, signal='TERM')

            timeout = time.time() + ECHO_SERVER_TIMEOUT
            pid_file = '/run/zephyr_echo_server.' + str(port) + '.pid'
            while self.vm_host.cli.exists(pid_file):
                time.sleep(1)
                if time.time() > timeout:
                    terminate_process(proc.process, signal='KILL')
                    break
            self.vm_host.cli.rm(pid_file)
            self.echo_server_procs[port] = None

    def send_echo_request(self, dest_ip='localhost', dest_port=DEFAULT_ECHO_PORT, echo_request='ping'):
        """
        Create a TCP connection to send specified request string to dest_ip on dest_port
        (defaults to localhost:80) and return the response.
        :param dest_ip: str
        :param dest_port: int
        :param echo_request: str
        :return: str
        """
        self.vm_host.LOG.debug('Sending echo command to: nc ' + str(dest_ip) + ' ' + str(dest_port))
        cmd0 = ['echo', '-n', echo_request]
        cmd1 = ['nc', dest_ip, str(dest_port)]
        ret = self.vm_host.cli.cmd_pipe(commands=[cmd0, cmd1]).stdout
        self.vm_host.LOG.debug('Received echo response: ' + ret)
        return ret

    def execute(self, cmd_line, timeout=None, blocking=True):
        """
        Execute the given cmd_line command on this guest, using an optional timeout
        and either blocking or non-blocking.
        :param cmd_line: str
        :param timeout: int
        :param blocking: bool
        :return:
        """
        result = self.vm_host.cli.cmd(cmd_line, timeout=timeout, blocking=blocking)
        if result.ret_code != 0:
            raise SubprocessFailedException('Retcode: ' + str(result.ret_code) +
                                            ', cmd output: ' + result.stdout +
                                            ', cmd error: ' + result.stderr)
        return result

    def terminate(self):
        """
        Kill this VM.
        :return:
        """
        for p in self.open_ports_by_id:
            self.vm_host.unplug_iface(p)
        self.open_ports_by_id.clear()
        self.vm_host.net_down()
        self.vm_host.shutdown()
        self.vm_host.remove()
