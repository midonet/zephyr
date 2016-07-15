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

import abc
import time
from zephyr.common import exceptions
from zephyr.common.zephyr_constants import DEFAULT_ECHO_PORT


class UnderlayHost(object):
    def __init__(self, name):
        self.name = name
        self.LOG = None
        self.main_ip = None

    def create_vm(self, ip, mac, gw_ip, name):
        return None

    def fetch_file(self, file_name, **kwargs):
        return None

    def get_hypervisor_name(self):
        return None

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        return None

    def del_route(self, route_ip):
        return None

    def create_interface(self, iface, mac=None, ip_list=None,
                         linked_bridge=None, vlans=None):
        return None

    def add_ip(self, iface_name, ip_addr):
        return None

    def get_ip(self, iface_name):
        return None

    def reset_default_route(self, ip_addr):
        return None

    def reboot(self):
        return None

    def start_echo_server(self, ip_addr='', port=DEFAULT_ECHO_PORT,
                          echo_data="pong", protocol='tcp'):
        """
        Start an echo server listening on given ip/port (default to
        localhost:80) which returns the echo_data on any TCP
        connection made to the port.
        :param ip_addr: str
        :param port: int
        :param echo_data: str
        :param protocol: str
        :rtype: bool
        """
        self.LOG.debug('Starting echo server on host [' + self.name +
                       '] on IP and port: ' +
                       (str(ip_addr) if ip_addr != '' else '*') +
                       ':' + str(port))
        self.do_start_echo_server(ip_addr, port, echo_data, protocol)
        timeout = time.time() + 5
        conn_resp = ''
        while conn_resp != 'connect-test:' + echo_data:
            try:
                conn_ip = ip_addr if ip_addr != '' else '127.0.0.1'
                conn_resp = self.send_echo_request(
                    dest_ip=conn_ip, dest_port=port,
                    echo_request='connect-test', protocol=protocol)
            except exceptions.SubprocessFailedException:
                conn_resp = ''

            if time.time() > timeout:
                out = self.stop_echo_server(ip_addr, port)
                stdout = out[0] if out else ''
                stderr = out[1] if out else ''
                self.LOG.error(
                    'Echo server listener failed to bind to port '
                    'within timeout (stdout/stderr): ' +
                    str(stdout.replace('\\n', '\n')) + " / " +
                    str(stderr.replace('\\n', '\n')))
                raise exceptions.SubprocessTimeoutException(
                    'Echo server listener failed to bind to port '
                    'within timeout (stdout/stderr): ' +
                    str(stdout.replace('\\n', '\n')) + " / " +
                    str(stderr.replace('\\n', '\n')))
        return True

    @abc.abstractmethod
    def do_start_echo_server(self, ip_addr='', port=DEFAULT_ECHO_PORT,
                             echo_data="pong", protocol='tcp'):
        return None

    def stop_echo_server(self, ip_addr='', port=DEFAULT_ECHO_PORT):
        """
        Stop an echo server that has been started on given ip/port (defaults to
        localhost:80).  If echo service has not been started, do nothing.
        :param ip_addr: str
        :param port: int
        :rtype: (file, file)
        """
        self.LOG.debug('Stopping echo server on host [' + self.name +
                       '] on IP and port: ' +
                       (str(ip_addr) if ip_addr != '' else '*') +
                       ':' + str(port))
        return self.do_stop_echo_server(ip_addr, port)

    @abc.abstractmethod
    def do_stop_echo_server(self, ip_addr='', port=DEFAULT_ECHO_PORT):
        return None

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=DEFAULT_ECHO_PORT,
                          echo_request='ping',
                          protocol='tcp', timeout=10):
        """
        Create a TCP connection to send specified request string to dest_ip
        on dest_port (defaults to localhost:80) and return the response.
        :param dest_ip: str
        :param dest_port: int
        :param echo_request: str
        :param protocol: str
        :param timeout: int
        :rtype: str
        """
        self.LOG.debug(
            'Sending TCP echo [' + echo_request +
            '] to far host IP: ' + dest_ip + ' on port: ' + str(dest_port))
        return self.do_send_echo_request(dest_ip, dest_port, echo_request,
                                         protocol, timeout)

    @abc.abstractmethod
    def do_send_echo_request(self, dest_ip='localhost',
                             dest_port=DEFAULT_ECHO_PORT,
                             echo_request='ping',
                             protocol='tcp', timeout=10):
        return None

    def send_custom_packet(self, iface, **kwargs):
        return None

    def send_arp_packet(self, iface, dest_ip, source_ip=None,
                        command='request',
                        source_mac=None, dest_mac=None,
                        packet_options=None, count=1):
        return None

    def send_tcp_packet(self, iface, dest_ip,
                        source_port, dest_port, data=None,
                        packet_options=None, count=1):
        return None

    def ping(self, target_ip, iface=None, count=1, timeout=None):
        return None

    def start_capture(self, interface, count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None, save_dump_file=False,
                      save_dump_filename=None):
        return None

    def capture_packets(self, interface, count=1, timeout=None):
        return None

    def stop_capture(self, interface):
        return None

    def flush_arp(self):
        return None

    def plugin_iface(self, iface, port_id):
        return None

    def unplug_iface(self, port_id):
        return None

    def execute(self, cmd_line, timeout=None, blocking=True):
        return None

    def terminate(self):
        return None
