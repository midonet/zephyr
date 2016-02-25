__author__ = 'vagrant'

import unittest

from common.EchoServer import *
from CBT.UnitTestRunner import run_unit_test


class EchoServerTest(unittest.TestCase):
    def test_echo_tcp(self):
        es = EchoServer()
        try:
            es.start(create_pid_file=False)

            ret = EchoServer.send(es.ip, es.port)
            self.assertEqual('ping:pong', ret)
        except Exception as e:
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
        except Exception as e:
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
