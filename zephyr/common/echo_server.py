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

import errno
import logging
import select
import socket
import threading
import time
from zephyr.common import exceptions

DEFAULT_ECHO_PORT = 5080
TIMEOUT = 2
TERMINATION_STRING = chr(0x03) + chr(0x04)
ECHO_SERVER_TIMEOUT = 3


class EchoServerListener(threading.Thread):
    def __init__(self, ip_addr, port, protocol, echo_data,
                 logger=None):
        super(EchoServerListener, self).__init__()
        self.ip_addr = ip_addr
        self.port = port
        self.protocol = protocol
        self.echo_data = echo_data
        self.running_event = threading.Event()
        self.stop_event = threading.Event()
        self.finished_event = threading.Event()
        self.error_event = threading.Event()
        self.error_event_list = []
        self.LOG = logger
        if not self.LOG:
            self.LOG = logging.getLogger("echo-server")
            self.LOG.addHandler(logging.NullHandler())
        self.running_event.clear()
        self.stop_event.clear()
        self.finished_event.clear()

    def run(self):
        if self.port < 1024:
            raise exceptions.ArgMismatchException(
                "Cannot start echo server on privileged port (<1024).")

        debug = True
        try:
            self.LOG.info('Listener Socket starting up')
            if self.protocol == 'tcp':
                _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # TODO(micucci): Enable UDP
            # elif self.protocol == 'udp':
            #     _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
            #                             socket.IPPROTO_UDP)
            else:
                raise exceptions.ArgMismatchException(
                    'Unsupported self.protocol: ' + self.protocol)
            _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            _socket.setblocking(0)
            _socket.bind((self.ip_addr, self.port))
            if self.protocol == 'tcp':
                _socket.listen(2)
                self.LOG.info('Listener TCP Socket listening')
            self.running_event.set()
            while not self.stop_event.is_set():
                ready_list, _, _ = select.select([_socket], [], [], 0)
                if ready_list:

                    if self.protocol == 'tcp':
                        debug and self.LOG.debug(
                            'Listener TCP Socket connected')
                        conn, addr = ready_list[0].accept()
                        conn.setblocking(0)

                    data = ''
                    addr = None
                    while True:
                        try:
                            if self.protocol == 'tcp':
                                new_data = conn.recv(
                                    1024, socket.MSG_WAITALL)
                            elif self.protocol == 'udp':
                                new_data, addr = _socket.recvfrom(
                                    1024, socket.MSG_WAITALL)
                        except socket.error as e:
                            if (e.args[0] == errno.EAGAIN or
                                    e.args[0] == errno.EWOULDBLOCK):
                                continue
                        debug and self.LOG.debug(
                            'Listener Socket read some ' +
                            self.protocol + ' data: ' + new_data)
                        pos = new_data.find(TERMINATION_STRING)
                        if pos != -1:
                            data += new_data[0:pos]
                            break
                        else:
                            data += new_data

                    debug and self.LOG.debug(
                        'Listener Socket received all  ' +
                        self.protocol + ' data: ' + data)

                    send_data = self.echo_data + TERMINATION_STRING
                    if self.protocol == 'tcp':
                        conn.sendall(data + ':' + send_data)
                    elif self.protocol == 'udp':
                        _socket.sendto(data + ':' + send_data, addr)

                    debug and self.LOG.debug(
                        'Listener Socket sent appended ' +
                        self.protocol + ' data: ' + send_data)

                    if self.protocol == 'tcp':
                        conn.close()
                    elif self.protocol == 'udp':
                        _socket.close()

            self.LOG.info('Listener Socket terminating')
            if self.protocol == 'tcp':
                _socket.shutdown(socket.SHUT_RDWR)
            _socket.close()
            self.finished_event.set()
        except Exception as e:
            self.LOG.info('SERVER ERROR: ' + str(e))
            self.error_event_list.append(e)
            self.error_event.set()

        except socket.error as e:
            self.LOG.info('SOCKET-SETUP ERROR: ' + str(e))
            self.error_event_list.append(e)
            self.error_event.set()

    def stop(self):
        self.stop_event.set()


class EchoServer(object):
    def __init__(self, ip_addr='localhost', port=DEFAULT_ECHO_PORT,
                 echo_data='pong', protocol='tcp'):
        super(EchoServer, self).__init__()
        self._socket = None
        self.current_listener = EchoServerListener(
            ip_addr=ip_addr,
            port=port,
            echo_data=echo_data,
            protocol=protocol)

        self.ip_addr = self.current_listener.ip_addr
        self.port = self.current_listener.port
        self.echo_data = self.current_listener.echo_data
        self.protocol = self.current_listener.protocol

    def start(self):
        if self.current_listener.finished_event.isSet():
            raise exceptions.SubprocessFailedException(
                "Can only start an echo server once!")

        self.current_listener.start()
        self.current_listener.running_event.wait(TIMEOUT)
        if not self.current_listener.running_event.is_set():
            raise exceptions.SubprocessTimeoutException(
                'TCP echo server did not start within timeout')

        timeout = time.time() + ECHO_SERVER_TIMEOUT
        conn_resp = ''
        while conn_resp != 'connect-test:' + self.echo_data:
            conn_resp = self.send(
                ip_addr=self.ip_addr, port=self.port,
                echo_request='connect-test',
                protocol=self.protocol)
            if time.time() > timeout:
                raise exceptions.SubprocessTimeoutException(
                    'Echo server listener failed to bind to port '
                    'within timeout')

    def stop(self, timeout=10.0):
        """
        Stop the echo server and wait until server signals it is finished.
        Throw SubprocessTimeoutException if server doesn't stop within timeout.
        """
        self.current_listener.stop()
        self.current_listener.join(timeout)
        if self.current_listener.is_alive():
            raise exceptions.SubprocessTimeoutException(
                "Echo server did not stop within timeout!")

    @staticmethod
    def send(ip_addr, port, echo_request='ping', protocol='tcp'):
        """
        Send echo data to the configured IP and port and return the response
        (should be "echo_request:echo_response")
        :param ip_addr: str
        :param port: int
        :param echo_request: str
        :param protocol: str
        :return:
        """
        req = echo_request + TERMINATION_STRING
        if protocol == 'tcp':
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect((ip_addr, port))
            new_socket.sendall(req)
        elif protocol == 'udp':
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            new_socket.sendto(req, (ip_addr, port))
        else:
            raise exceptions.ArgMismatchException(
                'Unsupported self.protocol: ' + protocol)
        data = ''
        if protocol == 'tcp':
            while True:
                new_data = new_socket.recv(2048)
                """ :type: str"""
                pos = new_data.find(TERMINATION_STRING)
                if pos != -1:
                    data += new_data[0:pos]
                    break
                else:
                    data += new_data

        elif protocol == 'udp':
                data, addr = new_socket.recvfrom(2048)

        new_socket.close()

        pos = data.find(TERMINATION_STRING)
        if pos != -1:
            out_str = data[0:pos]

        return data
