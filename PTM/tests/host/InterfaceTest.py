
import unittest
import time

from common.CLI import LinuxCLI
from PTM.host.Host import Host
from PTM.host.Interface import Interface


class InterfaceTest(unittest.TestCase):
    def test_use_active_iface(self):
        cli = LinuxCLI(log_cmd=True)
        h = Host('test', None, cli, lambda name: None, lambda name: None)
        i = Interface('testi', h, ip_addr=['192.168.0.2'])
        cli.cmd('ip l add dev testi type dummy')
        self.assertTrue(cli.grep_cmd('ip l | grep testi', 'state DOWN'))

        i.up()

        time.sleep(1)
        self.assertTrue(cli.grep_cmd('ip l | grep testi', 'UP'))

        i.down()

        self.assertFalse(cli.grep_cmd('ip l | grep testi', 'UP'))

        cli.cmd('ip l del testi')

    def tearDown(self):
        LinuxCLI().cmd('ip l del testi')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(InterfaceTest)
