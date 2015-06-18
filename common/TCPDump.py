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
import common.Utils

import multiprocessing
import subprocess
import threading
import os
import Queue
from fcntl import fcntl, F_GETFL, F_SETFL
import signal

import time


def sig_handler():
    with open('tcpdump.out', 'a') as f:
        f.write("in signal handler")
    raise IOError("I/O error")


def parse_line_to_byte_array(line):
    byte_data = []
    data = [l.strip() for l in line.split(':', 2)]
    if len(data) == 2:
        for octet_pair in data[1].split():
            lbyte = int(octet_pair[0:2], 16)
            byte_data.append(lbyte)
            if (len(octet_pair) > 2):
                hbyte = int(octet_pair[2:4], 16)
                byte_data.append(hbyte)
    return byte_data


def tcpdump_start(kwarg_map):
    try:
        return TCPDump._read_packet(**kwarg_map)
    except Exception as e:
        print 'Exception occured in subprocess: ' + e.message
        return 1


class TCPDump(object):

    def __init__(self):
        self.process = None
        """ :type: multiprocessing.Process"""

    def start_capture(self, cli=LinuxCLI(), interface='any',
                      count=0, packet_type='', pcap_filter=None, max_size=0,
                      timeout=None, callback=None, callback_args=None, blocking=False,
                      save_dump_file=False, save_dump_filename=None):
        """
        Capture <count> packets using tcpdump and add them to a Queue of PCAPPackets.
        Use wait_for_packets to retrieve the packets as a list (or wait for them to come in.
        The filter parameter should be a set of PCAP_Rules which can be combined to create
        practically any pcap_filter ruleset.  A callback may also be provided which must
        be a callable which takes at least a single PCAPPacket as an argument.  This callable
        will be called when each packet arrives along with any provided arguments (as a
        list).  A timeout may be provided in case of a blocking call, which will limit the
        blocking call to timeout seconds.  This time limit only applies to the execution of
        tcpdump if blocking is set to True.  The optional save_dump_file parameter can be
        set to true to save the temporary packet capture file to the given save file name
        (use tcp.out.<timestamp> if name not provided)

        :type cli: LinuxCLI
        :type interface: str
        :type count: int
        :type packet_type: str
        :type pcap_filter: PCAP_Rule
        :type max_size: int
        :type timeout: int
        :type callback: callable
        :type callback_args: list[T]
        :type blocking: bool
        :type save_dump_file: bool
        :type save_dump_filename: str
        :return:
        """
        # Don't run twice in a row
        if self.process is not None:
            raise SubprocessFailedException('tcpdump process already started')

        # Set up synchronization queues and events
        self.data_queue = multiprocessing.Queue()
        self.subprocess_info_queue = multiprocessing.Queue()

        self.tcpdump_ready = multiprocessing.Event()
        self.tcpdump_error = multiprocessing.Event()
        self.tcpdump_stop = multiprocessing.Event()
        self.tcpdump_finished = multiprocessing.Event()

        self.tcpdump_ready.clear()
        self.tcpdump_error.clear()
        self.tcpdump_stop.clear()
        self.tcpdump_finished.clear()

        kwarg_map = {'cli': cli,
                     'interface': interface,
                     'count': count,
                     'packet_type': packet_type,
                     'pcap_filter': pcap_filter,
                     'max_size': max_size,
                     'flag_set': (self.tcpdump_ready, self.tcpdump_error, self.tcpdump_stop, self.tcpdump_finished),
                     'packet_queues': (self.data_queue, self.subprocess_info_queue),
                     'callback': callback,
                     'callback_args': callback_args,
                     'save_dump_file': save_dump_file,
                     'save_dump_filename': save_dump_filename
                     }
        self.process = multiprocessing.Process(target=tcpdump_start, args=(kwarg_map,))
        self.process.start()

        deadline_time = time.time() + 10
        while not self.tcpdump_ready.is_set():
            if time.time() > deadline_time:
                raise SubprocessFailedException("tcpdump failed to start within 10 seconds")
            if self.tcpdump_error.is_set():
                print 'ERRROR!!!'
                error_info = self.subprocess_info_queue.get(timeout=2)
                if 'error' in error_info:
                    raise SubprocessFailedException('tcpdump error { ' +
                                                    'retcode[' + str(error_info['returncode']) + '] ' +
                                                    'reason [' + error_info['error'] + '] ' +
                                                    'stdout [' + error_info['stdout'] + '] ' +
                                                    'stderr [' + error_info['stderr'] + '] }')
                raise SubprocessFailedException('tcpdump error UNKNOWN')
            time.sleep(0)

        if blocking is True:
            self.process.join(timeout)
            if self.process.is_alive():
                raise SubprocessTimeoutException('tcpdump failed to receive packets within timeout')

    def wait_for_packets(self, count=1, timeout=None):
        ret = []
        start_time = time.time()
        while len(ret) < count:
            try:
                item = self.data_queue.get_nowait()
            except Queue.Empty:
                if timeout is not None:
                    if time.time() > start_time + timeout:
                        raise SubprocessTimeoutException((('Only ' + str(len(ret)) + '/') if len(ret) != 0 else '0/') +
                                                         str(count) + ' packets received within timeout')
                time.sleep(0)
            else:
                ret.append(item)

        return ret

    def stop_capture(self):
        """
        Stop the tcpdump process and return the old process object

        :return: multiprocessing.Process
        """
        # Signal the tcpdump loop to finish
        self.tcpdump_stop.set()

        # Join the thread and if it hasn't finished already, kill it
        self.process.join(5)
        if self.process.is_alive():
            self.process.terminate()
        ret = self.process
        self.process = None
        return ret

    @staticmethod
    def _read_packet(cli=LinuxCLI(), flag_set=None, interface='any',
                     count=1, packet_type='', pcap_filter=None, max_size=0,
                     packet_queues=None, callback=None, callback_args=None,
                     save_dump_file=False, save_dump_filename=None):

        tmp_dump_filename = './.tcpdump.out.' + str(time.time())

        try:
            # If flag set provided, use them instead, for synch with external functions
            tcp_ready = threading.Event() if flag_set is None else flag_set[0]
            tcp_error = threading.Event() if flag_set is None else flag_set[1]
            tcp_stop = threading.Event() if flag_set is None else flag_set[2]
            tcp_finished = threading.Event() if flag_set is None else flag_set[3]

            # If queue set provided, use them instead for synch with external functions
            packet_queue = Queue.Queue() if packet_queues is None else packet_queues[0]
            status_queue = Queue.Queue() if packet_queues is None else packet_queues[1]

            count_str = ('-c ' + str(count) if count > 0 else '')
            iface_str = '-i ' + interface
            max_size_str = '-s ' + max_size if max_size != 0 else ''
            type_str = '-T ' + packet_type if packet_type != '' else ''

            cmd_str = 'tcpdump -n -xx -l ' + \
                      count_str + ' ' + iface_str + ' ' + \
                      max_size_str + ' ' + type_str + \
                      (pcap_filter.to_str() if pcap_filter is not None else '') + \
                      ' >> ' + tmp_dump_filename

            cli.print_cmd = True

            # FLAG STATE: ready[clear], stop[clear], finished[clear]

            with open(tmp_dump_filename, 'w') as f:
                f.write("--START--\n")

            tcp_process = cli.cmd(cmd_line=cmd_str, blocking=False)

            flags_se = fcntl(tcp_process.stderr, F_GETFL) # get current p.stderr flags
            fcntl(tcp_process.stderr, F_SETFL, flags_se | os.O_NONBLOCK)

            err_out = ''
            while tcp_ready.is_set() is False:
                try:
                    line = os.read(tcp_process.stderr.fileno(), 256)
                    if line.find('listening on') != -1:
                        # TODO: Replace sleep after TCPDump starts with a real check
                        # This is dangerous, and might not actually be enough to signal the
                        # tcpdump is actually running.  Instead, let's create a Cython module that
                        # passes calls through to libpcap (there are 0 good libpcap implementations
                        # for Python that are maintained, documented, and simple).
                        time.sleep(1)
                        tcp_ready.set()
                    else:
                        err_out += line
                        if tcp_process.poll() is not None:
                            out, err = tcp_process.communicate()
                            status_queue.put({'error': 'tcpdump exited abnormally',
                                              'returncode': tcp_process.returncode,
                                              'stdout': out,
                                              'stderr': err_out})
                            print 'item on status queue'
                            tcp_error.set()

                            raise SubprocessFailedException('tcpdump exited abnormally with status: ' +
                                                            str(tcp_process.returncode))
                        time.sleep(0)

                except OSError:
                    pass

            # FLAG STATE: ready[set], stop[clear], finished[clear]

            # tcpdump return output format:
            # hh:mm:ss.tick L3Proto <Proto-specific fields>\n
            # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n <- eight quads of hexadecimal numbers
            # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n    representing 16 bytes or 4 32-bit words
            # hh:mm:ss.tick L3Proto <Proto-specific fields>\n        <- Next packet
            # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n
            # \t0x<addr>:  FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF\n

            packet_data = []
            timestamp = ''
            with open(tmp_dump_filename, 'r+') as f:
                # Prepare for the first packet by reading the file until the first
                # packet's lines arrive (or until stopped by a stop_capture call)
                if f.readline().rstrip() != '--START--':
                    status_queue.put({'error': 'Expected --START-- tag at beginning of dumpfile',
                                      'returncode': tcp_process.returncode,
                                      'stdout': '',
                                      'stderr': ''})
                    tcp_error.set()
                    raise ArgMismatchException('Expected --START-- tag at beginning of dumpfile')

                while True:
                    # Read the lines and either append data, start a new packet, or finish
                    line = f.readline()

                    if line == '':
                        #EOF

                        # Is the tcpdump process finished or signaled to finish?
                        if tcp_process.poll() is not None or tcp_stop.is_set():
                            if tcp_process.poll() is None:
                                # Kill the TCP subprocess if it is still running
                                common.Utils.terminate_process(tcp_process)

                            # If we finished with packet data buffered up, append that packet to the queue
                            if len(packet_data) > 0:
                                # Create and parse the packet and push it onto the return list, calling
                                # the callback function if one is set.
                                packet = PCAPPacket(packet_data, timestamp)
                                packet.parse()
                                packet_queue.put(packet)
                                if callback is not None:
                                    callback(packet, *(callback_args if callback_args is not None else ()))

                            # Stop packet collection and exit
                            break

                        # Otherwise, we need to wait for data
                        time.sleep(0)

                    elif line.startswith('\t'):
                        # Normal packet data: buffer into current packet
                        packet_data += parse_line_to_byte_array(line)
                    else:
                        # We hit the end of the packet and will start a new packet
                        # Only run if we had packet data buffered
                        if len(packet_data) > 0:
                            # Create and parse the packet and push it onto the return list, calling
                            # the callback function if one is set.
                            packet = PCAPPacket(packet_data, timestamp)
                            packet.parse()
                            packet_queue.put(packet)
                            if callback is not None:
                                callback(packet, *(callback_args if callback_args is not None else []))
                            packet_data = []

                        # Start the new packet by reading the timestamp
                        timestamp = line.split(' ', 2)[0]
        finally:
            # Save the tcpdump output (if requested) and delete the temporary file
            if save_dump_file is True:
                LinuxCLI().copy_file(tmp_dump_filename,
                                     save_dump_filename if save_dump_filename is not None
                                     else 'tcp.out.' + str(time.time()))

            LinuxCLI().rm(tmp_dump_filename)


        status_queue.put({'success': '',
                          'returncode' : tcp_process.returncode,
                          'stdout': tcp_process.stdout,
                          'stderr': tcp_process.stderr})

        # FLAG STATE: ready[set], stop[set], finished[clear]
        tcp_finished.set()

        # FLAG STATE: ready[set], stop[set], finished[set]
        return packet_queue

