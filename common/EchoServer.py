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

DEFAULT_ECHO_PORT = 5080
TIMEOUT = 2


def echo_server_listener(ip, port, echo_data, running_event, stop_event, finished_event):
    _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _socket.setblocking(False)
    _socket.bind((ip, port))
    _socket.listen(1)
    running_event.set()
    while not stop_event.is_set():
        ready_list, _, _ = select.select([_socket], [], [], 0)
        if len(ready_list) == 0:
            time.sleep(1)
            continue
        conn, addr = ready_list[0].accept()
        data = conn.recv(1024)
        conn.sendall(data + ':' + echo_data)
        conn.close()

    _socket.shutdown(socket.SHUT_RDWR)
    _socket.close()
    finished_event.set()


class EchoServer(object):
    def __init__(self, ip='localhost', port=DEFAULT_ECHO_PORT, echo_data='pong'):
        super(EchoServer, self).__init__()
        self.ip = ip
        self.port = port
        self.echo_data = echo_data
        self._socket = None
        self.server_process = None
        self.stop_server = multiprocessing.Event()
        self.server_done = multiprocessing.Event()
        self.server_running = multiprocessing.Event()

    def start(self):
        self.stop_server.clear()
        self.server_done.clear()
        self.server_running.clear()
        self.server_process = multiprocessing.Process(target=echo_server_listener,
                                                      args=(self.ip, self.port, self.echo_data,
                                                            self.server_running, self.stop_server, self.server_done))
        self.server_process.start()
        self.server_running.wait(TIMEOUT)
        if not self.server_running.is_set():
            raise SubprocessTimeoutException('TCP echo server did not start within timeout')

    def stop(self):
        """
        Stop the echo server and wait until server signals it is finished.  Throw
        SubprocessTimeoutException if server doesn't stop within timeout.
        """
        self.stop_server.set()
        self.server_done.wait(TIMEOUT)
        if not self.server_done.is_set():
            raise SubprocessTimeoutException('TCP echo server did not start within timeout')

        self.server_process.join()

    @staticmethod
    def send(ip, port, echo_request='ping'):
        """
        Send echo data to the configured IP and port and return the response (should be
        "echo_request:echo_response")
        :param echo_data:
        :return:
        """
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.connect((ip, port))
        new_socket.sendall(echo_request)
        data = ''
        while 1:
            new_data = new_socket.recv(2048)
            if not new_data:
                break
            data += new_data
        new_socket.close()
        return data
