__author__ = 'micucci'

import unittest

from PTM.Host import *
from PTM.MNRootServer import MNRootServer
from PTM.PhysicalTopologyConfig import HostDef

class HostTest(unittest.TestCase):
    def test_send_packet(self):
        rs = MNRootServer()
        h1 = rs.config_generic_host(HostDef('host1', [InterfaceDef(name='eth0', ip_list=[IPDef('10.0.1.2')])]))
        """ :type: Host"""
        h2 = rs.config_generic_host(HostDef('host2', [InterfaceDef(name='eth0', ip_list=[IPDef('10.0.1.3')])]))
        h1.send_packet('eth0', 'icmp', '10.0.1.3')
        self.assertEqual(True, False)

    def test_connect_iface_to_port(self):
        self.assertEqual(True, False)

if __name__ == '__main__':
    unittest.main()
