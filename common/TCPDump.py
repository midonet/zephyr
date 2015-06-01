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
import threading
import os
from fcntl import fcntl, F_GETFL, F_SETFL

import time

def tcpdump(data_q, tcp_event, timeout, **kwargs):
    packet = TCPDump.read_packet(timeout=timeout,
                                 tcp_ready=tcp_event, **kwargs)
    data_q.put(packet)

class TCPDump(object):

    def __init__(self):
        self.process = None

    def start_capture(self, timeout=None, blocking=False, **kwargs):
        self.data_queue = multiprocessing.Queue()

        if self.process is not None:
            raise SubprocessFailedException('tcpdump process already started')

        tcpdump_ready = multiprocessing.Event()
        tcpdump_ready.clear()
        self.process = multiprocessing.Process(target=tcpdump,
                                               args=(self.data_queue, tcpdump_ready, timeout),
                                               kwargs=kwargs)
        self.process.daemon = True
        self.process.start()
        if tcpdump_ready.wait(timeout) is False:
            raise SubprocessFailedException("tcpdump failed to start within timeout")

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
    def read_packet(cli=LinuxCLI(), tcp_ready=None, interface='any', max_size=0,
                    count=1, packet_type='', pcap_filter=PCAP_Null(), timeout=None):
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
        :param tcp_ready: multiprocessing.Event Flag to set when tcpdump is ready, 'None' to not set any flag
        :return: list[PCAPPacket]
        """
        count_str = '-c ' + str(count)
        iface_str = '-i ' + interface
        max_size_str = '-s ' + max_size if max_size != 0 else ''
        type_str = '-T ' + packet_type if packet_type != '' else ''

        cmd_str = 'tcpdump -n -xx -l ' + count_str + ' ' + iface_str + ' ' + \
                  max_size_str + ' ' + type_str + pcap_filter.to_str()
        cli.print_cmd = True
        p = cli.cmd(cmd_line=cmd_str, return_output=True, timeout=timeout, blocking=False)

        flags_se = fcntl(p.stderr, F_GETFL) # get current p.stderr flags
        fcntl(p.stderr, F_SETFL, flags_se | os.O_NONBLOCK)

        if tcp_ready is not None:
            while tcp_ready.is_set() is False:
                try:
                    line = os.read(p.stderr.fileno(), 256)
                    if line.find('listening on') != -1:
                        #TODO: Replace sleep after TCPDump starts with a real check
                        # This is dangerous, and might not actually be enough to signal the
                        # tcpdump is actually running.  Instead, let's create a Cython module that
                        # passes calls through to libpcap (there are 0 good libpcap implementations
                        # for Python that are maintained, documented, and simple).
                        time.sleep(1)
                        tcp_ready.set()
                except OSError:
                    pass

        out = ''
        for line in p.stdout:
            out += line

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

        for line in out.split('\n'):
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
                        byte_data.append(lbyte)
                        if (len(octet_pair) > 2):
                            hbyte = int(octet_pair[2:4], 16)
                            byte_data.append(hbyte)

        return packet_list

