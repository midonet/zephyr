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

from common.EchoServer import EchoServer, DEFAULT_ECHO_PORT

import getopt
import sys
import signal

arg_map, _ = getopt.getopt(sys.argv[1:], 'i:p:d:')

ip = 'localhost'
port = DEFAULT_ECHO_PORT
data = "pong"

for arg, value in arg_map:
    if arg in ('-i'):
        ip = value
    elif arg in ('-p'):
        port = int(value)
    elif arg in ('-d'):
        data = value

def term_handler(signum, frame):
    print "Exiting..."
    es.stop()
    exit(0)

signal.signal(signal.SIGTERM, term_handler)

es = EchoServer(ip, port, data)
es.start()
ret = ''
while ret != 'quit':
    ret = raw_input("Enter 'quit' to stop server...").strip()

es.stop()
print "Exiting..."
