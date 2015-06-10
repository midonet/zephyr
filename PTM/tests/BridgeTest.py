__author__ = 'micucci'

import unittest

from common.CLI import *
from common.Exceptions import *
from PTM.Host import Host
from PTM.Interface import Interface
from PTM.Bridge import Bridge

class BridgeTest(unittest.TestCase):
    def test_create(self):
        h = Host('test', LinuxCLI(), lambda name: None, lambda name: None)
        i = Interface('testi', h, None, ['192.168.0.2'])

        i.create()

        self.assertTrue(LinuxCLI().grep_cmd('ip l', 'testi'))

        b = Bridge('test-bridge', h, ip_addr=['192.168.0.240'], options=['stp'])

        b.create()

        # Check bridge is present
        self.assertTrue(h.cli.grep_cmd('brctl show | grep test-bridge | cut -f 1', 'test-bridge'))
        # Check STP
        self.assertTrue(h.cli.grep_cmd('brctl show | grep test-bridge | cut -f 4', 'yes'))

        b.link_interface(i)

        # Check interface has bridge set as link
        self.assertTrue(h.cli.grep_cmd('ip l | grep testi', 'test-bridge'))

        b.remove()
        i.remove()

if __name__ == '__main__':
    unittest.main()
