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
from common.CLI import LinuxCLI
from common.PCAPRules import *
from common.PCAPPacket import *

import multiprocessing

def tcpdump(data_q, timeout, **kwargs):
    packet = TCPDump.read_packet(timeout=timeout, **kwargs)
    data_q.put(packet)
    print 'Here'

class TCPDump(object):

    def __init__(self):
        self.process = None

    def start_capture(self, timeout=None, blocking=False, **kwargs):
        self.data_queue = multiprocessing.Queue()
        if self.process is not None:
            raise SubprocessFailedException('tcpdump process already started')
        self.process = multiprocessing.Process(target=tcpdump, args=(self.data_queue, timeout), kwargs=kwargs)
        self.process.start()
        if blocking is True:
            self.process.join()
        return self.data_queue

    def stop_capture(self, term=False):
        if self.process is None:
            raise SubprocessFailedException('tcpdump process not started')

        if term is True:
            self.process.terminate()
        else:
            self.process.join()
        self.process = None

    @staticmethod
    def read_packet(cli=LinuxCLI(), interface='any', max_size=0, count=1, packet_type='',
                    pcap_filter=PCAP_Null(),
                    timeout=None):
        """
        Sniff packets on an interface and return the data (optionally returning ALL packet data
        as well).  Returns a list, <count> in length, of matching data (or the entire packet data
        including headers if the include_packet_data option is set to True) in the form of
        (timestamp, data) for each member of the list.

        :param cli: LinuxCLI Specific CLI to run the command on. Defaults to root host.
        :param interface: str Interface to sniff on.  Defaults to 'any'.
        :param max_size: int Maximum length of data to return in each packet, no limit by default.
        :param count: int Number of packets matching filter to return, 1 by default.
        :param packet_type: str If set, watch for a particular specialized packet type (e.g. 'vxlan')
        :param pcap_filter: PCAP_Rule Rule object (corresponding to PCAP rulesets) to filter the packets
        :param timeout: int Time to wait for packet in seconds, 'None' for indefinite (default)
        :return: list[PCAPPacket]
        """
        count_str = '-c ' + str(count)
        iface_str = '-i ' + interface
        max_size_str = '-s ' + max_size if max_size != 0 else ''
        type_str = '-T ' + packet_type if packet_type != '' else ''

        cmd_str = 'tcpdump -n -xx -l ' + count_str + ' ' + iface_str + ' ' + \
                  max_size_str + ' ' + type_str + pcap_filter.to_str()
        cli.print_cmd = True
        ret_data = cli.cmd(cmd_line=cmd_str, return_output=True, timeout=timeout)

        packet_list = []
        byte_data = []
        timestamp = 0

        # tcpdump return output format:
        # hh:mm:ss.tick L3Proto <Proto-specific fields>\n
        # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n <- eight quads of hexadecimal numbers
        # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n    representing 16 bytes or 4 32-bit words
        # hh:mm:ss.tick L3Proto <Proto-specific fields>\n        <- Next packet
        # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n
        # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n

        for line in ret_data.split('\n'):
            if not line.startswith('\t'):
                if len(byte_data) != 0:
                    # If we already have byte_data, then parse it and push the packet onto the return list
                    # Then reset the byte data to empty so we can start the next packet.
                    p = PCAPPacket(byte_data, timestamp)
                    p.parse()
                    packet_list.append(p)
                    byte_data = []
                timestamp = line.split(' ', 2)[0]
            else:
                data = [l.strip() for l in line.split(':', 2)]
                if len(data) == 2:
                    for octet_pair in data[1].split():
                        lbyte = int(octet_pair[0:2], 16)
                        hbyte = int(octet_pair[2:4], 16)
                        byte_data.append(lbyte)
                        byte_data.append(hbyte)

        return packet_list

