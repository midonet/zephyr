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
from zephyr.common import exceptions
from zephyr.common.zephyr_constants import DEFAULT_ECHO_PORT

PACKET_CAPTURE_TIMEOUT = 10


class Guest(object):
    """
    A class to wrap a VM from the Physical Topology Manager
    """

    def __init__(self, vm_underlay):
        self.vm_underlay = vm_underlay
        """ :type: zephyr.vtm.underlay.underlay_host.UnderlayHost"""
        self.open_ports_by_id = set()
        """ :type: set[str]"""
        self.main_ip = vm_underlay.get_ip('eth0')
        self.name = vm_underlay.name

    def plugin_vm(self, iface, port_id):
        """Links an interface on this VM to a virtual network port
            * bind interface to MidoNet with mm-ctl
            * set iface to the indicated mac address (if provided)
        :type iface: str
        :type port_id: str
        """
        self.vm_underlay.LOG.debug("Plugging in VM interface: " + iface +
                                   " to port: " + str(port_id))
        self.vm_underlay.plugin_iface(iface, port_id)
        self.open_ports_by_id.add(port_id)

    def unplug_vm(self, port_id):
        """Unlinks a port on this VM from the virtual network
        :type port_id: str
        """
        self.vm_underlay.LOG.debug("Unplugging VM port: " + str(port_id))
        self.vm_underlay.unplug_iface(port_id)
        self.open_ports_by_id.remove(port_id)

    def get_hypervisor_name(self):
        return self.vm_underlay.get_hypervisor_name()

    def clear_arp(self):
        return self.vm_underlay.flush_arp()

    def send_arp_request(self, on_iface, ip):
        return self.vm_underlay.send_arp_packet(iface=on_iface, dest_ip=ip,
                                                command='request', count=1)

    def send_arp_reply(self, on_iface, src_mac, dest_mac, src_ip, dest_ip):
        return self.vm_underlay.send_arp_packet(
            iface=on_iface, dest_ip=dest_ip,
            source_ip=src_ip, source_mac=src_mac, dest_mac=dest_mac,
            command='reply', count=1)

    def send_packet(self, on_iface='eth0', **kwargs):
        return self.vm_underlay.send_custom_packet(iface=on_iface, **kwargs)

    def send_tcp_packet(self, on_iface='eth0', data=None,
                        dest_ip=None,
                        source_port=None, dest_port=None,
                        packet_options=None, count=None):
        return self.vm_underlay.send_tcp_packet(
            iface=on_iface, dest_ip=dest_ip,
            source_port=source_port, dest_port=dest_port,
            data=data, packet_options=packet_options, count=count)

    def start_capture(self, on_iface='eth0',
                      count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None,
                      save_dump_file=False, save_dump_filename=None):
        """
        :param on_iface: str: Interface to capture on ('any' is
        also acceptable)
        :param count: int: Number of packets to capture, or '0' to capture
        until explicitly stopped (default)
        :param ptype: str: Type of packet to filter
        :param pfilter: PcapRule: Ruleset for packet filtering
        :param callback: callable: Optional callback function
        :param callback_args: list[T]: Arguments to optional callback function
        :param save_dump_file: bool: Optionally save the temporary packet
        capture file
        :param save_dump_filename: str: Filename to save temporary packet
        capture file
        """
        self.vm_underlay.start_capture(interface=on_iface,
                                       count=count, ptype=ptype,
                                       pfilter=pfilter, callback=callback,
                                       callback_args=callback_args,
                                       save_dump_file=save_dump_file,
                                       save_dump_filename=save_dump_filename)

    def capture_packets(self, on_iface='eth0', count=1,
                        timeout=PACKET_CAPTURE_TIMEOUT):
        """
        Capture (count) number of packets that have come into the given
        interface on an running capture (raises ObjectNotFoundException if
        capture isn't running already), or wait (timeout) seconds for all
        the packets to arrive.  Returns the packet list and throws a
        SubprocessTimeoutException if the packets do not all arrive in time.
        :param on_iface: str
        :param count: int
        :param timeout: int
        :return: list[PCAPPacket]
        """
        return self.vm_underlay.capture_packets(
            interface=on_iface, count=count,
            timeout=timeout)

    def stop_capture(self, on_iface='eth0'):
        """
        Stop an already running capture, do nothing if capture is not running
        on interface.
        :param on_iface: str
        """
        self.vm_underlay.stop_capture(interface=on_iface)

    def verify_connection_to_host(self, far_host,
                                  target_ip_addr=None,
                                  target_port=DEFAULT_ECHO_PORT,
                                  use_icmp=True, use_tcp=True,
                                  timeout=20):
        target_ip = target_ip_addr if target_ip_addr else far_host.main_ip

        if use_tcp:
            deadline = time.time() + timeout
            far_host.start_echo_server(
                ip_addr="", port=target_port)
            try:
                replied = False
                while not replied:
                    try:
                        if time.time() > deadline:
                            return False
                        reply = self.send_echo_request(
                            dest_ip=target_ip,
                            dest_port=target_port)
                        if reply != "":
                            replied = True
                    except exceptions.SubprocessFailedException:
                        pass
            finally:
                far_host.stop_echo_server(
                    ip_addr="", port=target_port)

        if use_icmp:
            deadline = time.time() + timeout
            while not self.ping(
                    target_ip=target_ip, count=1, timeout=3):
                if time.time() > deadline:
                    return False

        return True

    def ping(self, target_ip, on_iface='eth0', count=3, timeout=None):
        """
        Ping the target_ip on given interface and return true if the ping
        succeeds, false otherwise.
        :param target_ip: str
        :param on_iface: str
        :param count: int
        :param timeout: int
        :return: bool
        """
        return self.vm_underlay.ping(target_ip=target_ip, iface=on_iface,
                                     count=count, timeout=timeout)

    def start_echo_server(self, ip_addr='localhost', port=DEFAULT_ECHO_PORT,
                          echo_data="pong", protocol='tcp'):
        """
        Start an echo server listening on given ip/port (default to
        localhost:80) with the given protocol, which returns the echo_data
        on any TCP connection made to the port.
        :param ip_addr: str
        :param port: int
        :param echo_data: str
        :param protocol: str
        :return: bool
        """
        return self.vm_underlay.start_echo_server(
            ip_addr, port, echo_data, protocol)

    def stop_echo_server(self, ip_addr='localhost', port=DEFAULT_ECHO_PORT):
        """
        Stop an echo server that has been started on given ip/port (defaults to
        localhost:80).  If echo service has not been started, do nothing.
        :param ip_addr: str
        :param port: int
        :return: (file, file) | None
        """
        return self.vm_underlay.stop_echo_server(ip_addr, port)

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=DEFAULT_ECHO_PORT,
                          echo_request='ping', protocol='tcp',
                          timeout=10):
        """
        Create a TCP connection to send specified request string over the
        specified protocol to dest_ip on dest_port (defaults to localhost:80)
        and return the response.
        :param dest_ip: str
        :param dest_port: int
        :param echo_request: str
        :param protocol: str
        :return: str
        """
        return self.vm_underlay.send_echo_request(
            dest_ip=dest_ip, dest_port=dest_port,
            echo_request=echo_request, protocol=protocol,
            timeout=timeout)

    def execute(self, cmd_line, timeout=None, blocking=True):
        """
        Execute the given cmd_line command on this guest, using an optional
        timeout and either blocking or non-blocking.
        :param cmd_line: str
        :param timeout: int
        :param blocking: bool
        :return:
        """
        result = self.vm_underlay.execute(cmd_line, timeout=timeout,
                                          blocking=blocking)
        """ :type: CommandStatus"""
        if result.ret_code != 0:
            raise exceptions.SubprocessFailedException(
                'Retcode: ' + str(result.ret_code) +
                ', cmd output: ' + result.stdout +
                ', cmd error: ' + result.stderr)
        return result

    def terminate(self):
        """
        Kill this VM.
        :return:
        """
        for p in self.open_ports_by_id:
            self.vm_underlay.unplug_iface(p)
        self.open_ports_by_id.clear()
        self.vm_underlay.terminate()
