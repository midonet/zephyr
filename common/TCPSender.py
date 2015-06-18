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

from common.CLI import LinuxCLI
from common.Exceptions import *

import multiprocessing

def send_packet(tcp_event, **kwargs):
    TCPSender.send_packet(tcp_ready=tcp_event, **kwargs)

class TCPSender(object):

    def __init__(self):
        self.process = None

    def start_send(self, blocking=True, **kwargs):
        if self.process is not None:
            raise SubprocessFailedException('tcp send process already started')

        tcp_ready = multiprocessing.Event()
        tcp_ready.clear()
        self.process = multiprocessing.Process(target=send_packet, args=(tcp_ready,), kwargs=kwargs)
        self.process.daemon = True
        self.process.start()
        if tcp_ready.wait(10) is False:
            raise SubprocessFailedException("mz failed to send within timeout")

        if blocking is True:
            self.process.join()

    def stop_send(self, term=False):
        if self.process is None:
            raise SubprocessFailedException('tcp send process not started')

        if term is True:
            self.process.terminate()
        else:
            self.process.join()
        self.process = None


    @staticmethod
    def send_packet(cli=LinuxCLI(), tcp_ready=None, interface='any', packet_type=None,
                    source_port=None, dest_port=None,
                    source_ip=None, dest_ip=None,  source_mac=None,
                    dest_mac=None, packet_options=None, count=None,
                    delay=None, byte_data=None, timeout=None):
        """
        :type cli: LinuxCLI
        :type interface: str
        :type packet_type: str
        :type source_port: int
        :type dest_port: int
        :type source_ip: str
        :type dest_ip: str
        :type source_mac: str
        :type dest_mac: str
        :type packet_options: dict[str, str]
        :type count: int
        :type delay: int
        :type byte_data: str
        :type timeout: int
        :return: str
        """

        count_str = '-c %d' % count if count is not None else ''
        src_mac_str = '-a %s' % source_mac if source_mac is not None else ''
        dest_mac_str = '-b %s' % dest_mac if dest_mac is not None else ''
        arg_str = ' '.join((src_mac_str, dest_mac_str, count_str))

        # Bytes-only mode, only -a, -b, -c, and -p are supported by mz
        if packet_type is None:
            if byte_data is None:
                raise ArgMismatchException('The "byte_data" parameter is required if "packet_type" is not present')
            full_cmd_str = 'mz %(iface)s %(arglist)s "%(bytes)s"' % \
                           {'iface': interface,
                            'arglist': arg_str,
                            'bytes': byte_data}
            out = cli.cmd(full_cmd_str, timeout=timeout)
            if tcp_ready is not None:
                tcp_ready.set()
            return out

        # Packet-builder mode, supports various opts (supported opts depend on packet type)
        pkt_type_str = '-t %s' % packet_type if packet_type is not None else ''
        src_ip_str = '-A %s' % source_ip if source_ip is not None else ''
        dest_ip_str = '-B %s' % dest_ip if dest_ip is not None else ''
        delay_str = '-d %d' % delay if delay is not None else ''
        pkt_bldr_arg_str = ' '.join((src_ip_str, dest_ip_str, src_mac_str, dest_mac_str, delay_str))
        opt_list = ', '.join('%s=%s' % (k, v)
                             for k, v in packet_options.iteritems()) if packet_options is not None else ''

        if packet_type is 'arp' or packet_type is 'icmp':
            if 'command' not in packet_options:
                raise ArgMismatchException('arp and icmp packets need a command or type')
            cmd_opt = packet_options.pop('command')
            opt_list = ', '.join('%s=%s' % (k, v)
                                 for k, v in packet_options.iteritems()) if packet_options is not None else ''
            cmd_str = cmd_opt + (', ' + opt_list if opt_list != '' else '')
        elif packet_type is 'tcp' or packet_type is 'udp':
            source_port_str = 'sp=%s' % source_port if source_port is not None else ''
            dest_port_str = 'dp=%s' % dest_port if dest_port is not None else ''
            cmd_str = ','.join((source_port_str, dest_port_str))
        else:
            cmd_str = ', '.join('%s=%s' % (k, v)
                                 for k, v in packet_options.iteritems()) if packet_options is not None else ''

        full_cmd_str = 'mz %(iface)s %(arglist)s %(extra_args)s %(pkttype)s "%(cmd)s"' % \
                       {'iface': interface,
                        'arglist': arg_str,
                        'extra_args': pkt_bldr_arg_str,
                        'pkttype': pkt_type_str,
                        'cmd': cmd_str}

        out = cli.cmd(full_cmd_str, timeout=timeout)
        if tcp_ready is not None:
            tcp_ready.set()
        return out
