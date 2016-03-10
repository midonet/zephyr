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

import unittest

from zephyr.common.echo_server import *
from zephyr.common.utils import run_unit_test


class EchoServerTest(unittest.TestCase):
    def test_echo_tcp(self):
        es = EchoServer()
        try:
            es.start(create_pid_file=False)

            ret = EchoServer.send(es.ip, es.port)
            self.assertEqual('ping:pong', ret)
        except Exception:
            raise
        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    # TODO(micucci): Get UDP working
    @unittest.skip("UDP is still not working right")
    def test_echo_udp(self):
        es = EchoServer(protocol='udp')
        try:
            es.start(create_pid_file=False)
            ret = EchoServer.send(es.ip, es.port, protocol='udp')
            self.assertEqual('ping:pong', ret)
        except Exception:
            raise
        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    def test_customized_echo(self):
        es = EchoServer(echo_data='test-back')
        try:
            es.start(create_pid_file=False)
            ret = es.send(es.ip, es.port, 'test-send')
            self.assertEqual('test-send:test-back', ret)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    def test_multiple_pings_tcp(self):
        es = EchoServer()
        try:
            es.start(create_pid_file=False)
            ret = es.send(es.ip, es.port)
            self.assertEqual('ping:pong', ret)

            ret2 = es.send(es.ip, es.port, 'ping2')
            self.assertEqual('ping2:pong', ret2)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    # TODO(micucci): Get UDP working
    @unittest.skip("UDP is still not working right")
    def test_multiple_pings_udp(self):
        es = EchoServer(protocol='udp')
        try:
            es.start(create_pid_file=False)
            ret = es.send(es.ip, es.port)
            self.assertEqual('ping:pong', ret)

            ret2 = es.send(es.ip, es.port, 'ping2')
            self.assertEqual('ping2:pong', ret2)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    def test_long_data_tcp(self):
        es = EchoServer()
        try:
            es.start(create_pid_file=False)
            data = 300 * '0123456789'
            ret = es.send(es.ip, es.port, echo_request=data)
            self.assertEqual(data + ':pong', ret)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    # TODO(micucci): Get UDP working
    @unittest.skip("UDP is still not working right")
    def test_long_data_udp(self):
        es = EchoServer(protocol='udp')
        try:
            es.start(create_pid_file=False)
            data = 300 * '0123456789'
            ret = es.send(es.ip, es.port, echo_request=data)
            self.assertEqual(data + ':pong', ret)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    def test_multiple_restarts(self):
        es = EchoServer()
        try:
            es.start(create_pid_file=False)
            ret = es.send(es.ip, es.port)
            self.assertEqual('ping:pong', ret)

            es.stop()

            self.assertTrue(es.server_done.is_set())

            es.start(create_pid_file=False)

            ret2 = es.send(es.ip, es.port, 'ping2')
            self.assertEqual('ping2:pong', ret2)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

run_unit_test(EchoServerTest)
