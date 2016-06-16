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

from zephyr.common.echo_server import DEFAULT_ECHO_PORT


class UnderlayHost(object):
    def __init__(self, name):
        self.name = name
        self.LOG = None

    def create_vm(self, ip, mac, gw_ip, name):
        pass

    def fetch_file(self, file_name, **kwargs):
        pass

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        pass

    def del_route(self, route_ip):
        pass

    def create_interface(self, iface, mac=None, ip_list=None,
                         linked_bridge=None, vlans=None):
        pass

    def add_ip(self, iface_name, ip_addr):
        pass

    def reset_default_route(self, ip_addr):
        pass

    def reboot(self):
        pass

    def start_echo_server(self, ip_addr='localhost', port=DEFAULT_ECHO_PORT,
                          echo_data="echo-reply", protocol='tcp'):
        pass

    def stop_echo_server(self, ip_addr='localhost', port=DEFAULT_ECHO_PORT):
        pass

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=DEFAULT_ECHO_PORT,
                          echo_request='ping', source_ip=None,
                          protocol='tcp'):
        pass

    def send_custom_packet(self, iface, **kwargs):
        pass

    def send_arp_packet(self, iface, dest_ip, source_ip=None,
                        command='request',
                        source_mac=None, dest_mac=None,
                        packet_options=None, count=1):
        pass

    def send_tcp_packet(self, iface, dest_ip,
                        source_port, dest_port, data=None,
                        packet_options=None, count=1):
        pass

    def ping(self, target_ip, iface=None, count=1, timeout=None):
        pass

    def start_capture(self, interface, count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None, save_dump_file=False,
                      save_dump_filename=None):
        pass

    def capture_packets(self, interface, count=1, timeout=None):
        pass

    def stop_capture(self, interface):
        pass

    def flush_arp(self):
        pass

    def plugin_iface(self, iface, port_id):
        pass

    def unplug_iface(self, port_id):
        pass

    def execute(self, cmd_line, timeout=None, blocking=True):
        pass

    def terminate(self):
        pass
