#!/usr/bin/env python
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

import getopt
import socket
import sys
import traceback
from zephyr.common import exceptions

DEFAULT_ECHO_PORT = 5080
TERMINATION_STRING = chr(0x03) + chr(0x04)

arg_map, _ = getopt.getopt(
    sys.argv[1:],
    'i:'
    'p:'
    'c:'
    'o:'
    't:',
    ['ip', 'port', 'protocol', 'timeout', 'out-str'])

ip_addr = 'localhost'
port = DEFAULT_ECHO_PORT
echo_request_string = "ping"
protocol = "tcp"
timeout = 5


for arg, value in arg_map:
    if arg in ('-i', 'ip'):
        ip_addr = value
    elif arg in ('-p', 'port'):
        port = int(value)
    elif arg in ('-c', 'protocol'):
        protocol = value
    elif arg in ('-t', 'timeout'):
        timeout = float(value)
    elif arg in ('-o', 'out-str'):
        echo_request_string = value
    else:
        raise exceptions.ArgMismatchException(
            "Option not recognized: " + arg)

try:
    req = echo_request_string + TERMINATION_STRING
    if protocol == 'tcp':
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.settimeout(timeout)
        new_socket.connect((ip_addr, port))
        new_socket.sendall(req)
    elif protocol == 'udp':
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        new_socket.settimeout(timeout)
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
    out_str = data
    if pos != -1:
        out_str = data[0:pos]

    print(out_str.strip())

except Exception as e:
    sys.stderr.write("ERROR: " + str(e))
    sys.stderr.flush()
    traceback.print_tb(sys.exc_traceback, file=sys.stderr)
    exit(2)
