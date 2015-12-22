__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import select
import multiprocessing
import time
import os
from common.Exceptions import *
from common.CLI import LinuxCLI

DEFAULT_ECHO_PORT = 5080
TIMEOUT = 2


def echo_server_listener(ip, port, protocol, echo_data, running_event, stop_event, finished_event):
    tmp_status_file_name = '/tmp/echo-server-status.' + str(port)
    debug = True
    _socket = None
    try:
        LinuxCLI().cmd('echo "Listener Socket starting up" >> ' + tmp_status_file_name)
        if protocol == 'tcp':
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TODO: Get UDP working
        # elif protocol == 'udp':
        #     _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            raise ArgMismatchException('Unsupported protocol: ' + protocol)
        _socket.setblocking(False)
        _socket.bind((ip, port))
        if protocol == 'tcp':
            _socket.listen(1)
            LinuxCLI().cmd('echo "Listener Socket listening" >> ' + tmp_status_file_name)
        running_event.set()
        while not stop_event.is_set():
            ready_list, _, _ = select.select([_socket], [], [], 0)
            if len(ready_list) > 0:
                if protocol == 'tcp':
                    debug and LinuxCLI().cmd('echo "Listener Socket connected" >> ' + tmp_status_file_name)
                    conn, addr = ready_list[0].accept()
                    data = conn.recv(1024)
                    debug and LinuxCLI().cmd('echo "Listener Socket received data: ' + data + '" >> ' + tmp_status_file_name)
                    conn.sendall(data + ':' + echo_data)
                    debug and LinuxCLI().cmd('echo "Listener Socket sent appended data: ' +
                                             echo_data + '" >> ' + tmp_status_file_name)
                    conn.close()
                # TODO: Get UDP working
                # elif protocol == 'udp':
                #     LinuxCLI().cmd('echo "Listener Socket waiting for UDP" >> ' + tmp_status_file_name)
                #     data, addr = _socket.recvfrom(1024)
                #     debug and LinuxCLI().cmd('echo "Listener Socket received UDP data: ' +
                #                              data + '" >> ' + tmp_status_file_name)
                #     if data != 'stop-server':
                #         _socket.sendto(data + ':' + echo_data, addr)
                #     debug and LinuxCLI().cmd('echo "Listener Socket sent appended UDP data: ' +
                #                              echo_data + ' to ' + str(addr) + '" >> ' + tmp_status_file_name)

        LinuxCLI().cmd('echo "Listener Socket terminating" >> ' + tmp_status_file_name)
        if protocol == 'tcp':
            _socket.shutdown(socket.SHUT_RDWR)
        _socket.close()
        finished_event.set()
    except Exception as e:
        LinuxCLI().cmd('echo "SERVER ERROR: ' + str(e) + '" >> ' + tmp_status_file_name)
        exit(2)
    except socket.error as e:
        LinuxCLI().cmd('echo "SOCKET-SETUP ERROR: ' + str(e) + '" >> ' + tmp_status_file_name)
        exit(2)

class EchoServer(object):
    def __init__(self, ip='localhost', port=DEFAULT_ECHO_PORT, echo_data='pong', protocol='tcp'):
        super(EchoServer, self).__init__()
        self.ip = ip
        self.port = port
        self.echo_data = echo_data
        self._socket = None
        self.server_process = None
        self.stop_server = multiprocessing.Event()
        self.server_done = multiprocessing.Event()
        self.server_running = multiprocessing.Event()
        self.run_dir = '/run'
        self.pid_file = self.run_dir + '/zephyr_echo_server.' + str(self.port) + '.pid'
        self.protocol = protocol

    def start(self, create_pid_file=True):
        self.stop_server.clear()
        self.server_done.clear()
        self.server_running.clear()
        self.server_process = multiprocessing.Process(target=echo_server_listener,
                                                      args=(self.ip, self.port, self.protocol,
                                                            self.echo_data,
                                                            self.server_running, self.stop_server, self.server_done))
        self.server_process.start()
        self.server_running.wait(TIMEOUT)
        if not self.server_running.is_set():
            raise SubprocessTimeoutException('TCP echo server did not start within timeout')
        if create_pid_file:
            LinuxCLI().write_to_file(self.pid_file, str(multiprocessing.current_process().pid))

    def stop(self):
        """
        Stop the echo server and wait until server signals it is finished.  Throw
        SubprocessTimeoutException if server doesn't stop within timeout.
        """
        self.stop_server.set()
        if self.protocol == 'udp':
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            new_socket.sendto("stop-server", (self.ip, self.port))
        self.server_done.wait(TIMEOUT)
        if not self.server_done.is_set():
            raise SubprocessTimeoutException('TCP echo server did not stop within timeout')

        self.server_process.join()

        if LinuxCLI().exists(self.pid_file):
            pid = LinuxCLI().read_from_file(self.pid_file)
            LinuxCLI().cmd('kill ' + str(pid))
            LinuxCLI().rm(self.pid_file)

    @staticmethod
    def send(ip, port, echo_request='ping', protocol='tcp'):
        """
        Send echo data to the configured IP and port and return the response (should be
        "echo_request:echo_response")
        :param ip: str
        :param port: int
        :param echo_request: str
        :param protocol: str
        :return:
        """
        new_socket = None
        if protocol == 'tcp':
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect((ip, port))
            new_socket.sendall(echo_request)
        elif protocol == 'udp':
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            new_socket.sendto(echo_request, (ip, port))
        else:
            raise ArgMismatchException('Unsupported protocol: ' + protocol)
        data = ''
        if protocol == 'tcp':
            while 1:
                new_data = new_socket.recv(2048)
                if not new_data:
                    break
                data += new_data

        elif protocol == 'udp':
                data, addr = new_socket.recvfrom(2048)

        new_socket.close()
        return data
