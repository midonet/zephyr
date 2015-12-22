__author__ = 'vagrant'

import unittest
from common.EchoServer import *


class EchoServerTest(unittest.TestCase):
    def test_basic_echo(self):
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

    # TODO: Get UDP working
    # def test_udp_echo(self):
    #     es = EchoServer(protocol='udp')
    #     try:
    #         es.start(create_pid_file=False)
    #         ret = EchoServer.send(es.ip, es.port, protocol='udp')
    #         self.assertEqual('ping:pong', ret)
    #     except Exception as e:
    #         raise
    #     finally:
    #         es.stop()
    #
    #     self.assertTrue(es.server_done.is_set())

    def test_customized_echo(self):
        es = EchoServer(echo_data='test-back')
        try:
            es.start(create_pid_file=False)
            ret = es.send(es.ip, es.port, 'test-send')
            self.assertEqual('test-send:test-back', ret)

        finally:
            es.stop()

        self.assertTrue(es.server_done.is_set())

    def test_multiple_pings(self):
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

from CBT.UnitTestRunner import run_unit_test
run_unit_test(EchoServerTest)
