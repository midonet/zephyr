__author__ = 'micucci'

import unittest

from common.CLI import LinuxCLI
from PTM.Host import Host
from PTM.Interface import Interface

class InterfaceTest(unittest.TestCase):
    def test_use_active_iface(self):
        h = Host('test',, LinuxCLI(), lambda name: None, lambda name: None
        i = Interface('testi', h, ip_addr=['192.168.0.2'])
        LinuxCLI().cmd('ip l add dev testi type dummy')
        self.assertTrue(LinuxCLI().grep_cmd('ip l | grep testi', 'state DOWN'))

        i.up()

        self.assertTrue(LinuxCLI().grep_cmd('ip l | grep testi', 'UP'))

        i.down()

        self.assertFalse(LinuxCLI().grep_cmd('ip l | grep testi', 'UP'))

        i.remove()

        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi'))


    def tearDown(self):
        LinuxCLI().cmd('ip l del testi')

if __name__ == '__main__':
    unittest.main()
