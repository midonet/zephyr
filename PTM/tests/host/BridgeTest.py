__author__ = 'micucci'

import unittest
import time
import datetime

from common.CLI import *
from PTM.host.Host import Host
from PTM.host.VirtualInterface import VirtualInterface
from PTM.host.Bridge import Bridge


class BridgeTest(unittest.TestCase):
    def test_create(self):
        cli = LinuxCLI()
        h = Host('test', None, cli, lambda name: None, lambda name: None)
        i = VirtualInterface('testi', host=h, ip_addr=['192.168.0.2'])

        i.create()
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=5)

        while not cli.grep_cmd('ip l', 'testi'):
            if datetime.datetime.now() > deadline:
                self.fail("Interface on bridge failed to be added within timeout")
            time.sleep(1)

        b = Bridge('test-bridge', h, ip_addr=['192.168.0.240'], options=['stp'])

        b.create()
        time.sleep(1)

        # Check bridge is present
        self.assertTrue(h.cli.grep_cmd('brctl show | grep test-bridge | cut -f 1', 'test-bridge'))
        # Check STP
        self.assertTrue(h.cli.grep_cmd('brctl show | grep test-bridge | cut -f 4', 'yes'))

        b.link_interface(i)
        time.sleep(1)
        # Check interface has bridge set as link
        self.assertTrue(h.cli.grep_cmd('ip l | grep testi', 'test-bridge'))

        b.remove()
        i.remove()

        self.assertFalse(cli.grep_cmd('ip l', 'testi'))
        self.assertFalse(cli.grep_cmd('brctl show', 'test-bridge'))

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip l del test-bridge')
        LinuxCLI().cmd('brctl delbr test-bridge')
        LinuxCLI().cmd('ip l del testi')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(BridgeTest)
