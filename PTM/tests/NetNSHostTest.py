__author__ = 'micucci'

import unittest
import os

from PTM.NetNSHost import *
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyConfig import *
from common.CLI import *
from PTM.Interface import Interface
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from common.LogManager import LogManager


class DummyInterface(Interface):
    def __init__(self, name, host, linked_bridge):
        super(DummyInterface, self).__init__(name, host, linked_bridge=linked_bridge)

    def create(self):
        self.cli.cmd('ip link add dev ' + self.get_name() + ' type dummy')
        # Add interface to the linked bridge, if there is one
        if self.linked_bridge is not None:
            self.linked_bridge.link_interface(self)


class NetNSHostTest(unittest.TestCase):
    def test_configure(self):

        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

        hcfg = HostDef('test',
                       bridges={'br0': BridgeDef('br0')},
                       interfaces={'testi': InterfaceDef('testi', ['192.168.1.2'], linked_bridge='br0')})
        icfg = ImplementationDef('test', 'NetNSHost')

        # Get the impl details and use that to instance a basic object
        h = NetNSHost(hcfg.name, ptm)
        log = lm.add_file_logger('test.log', 'test')
        h.set_logger(log)

        # Now configure the host with the definition and impl configs
        h.config_from_ptc_def(hcfg, icfg)

    def test_boot_shutdown(self):

        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

        hcfg = HostDef('test',
                       bridges={'br0': BridgeDef('br0')},
                       interfaces={'testi': InterfaceDef('testi', ['192.168.1.2'], linked_bridge='br0')})
        icfg = ImplementationDef('test', 'NetNSHost')

        h = NetNSHost(hcfg.name, ptm)
        log = lm.add_file_logger('test.log', 'test')
        h.set_logger(log)

        # Now configure the host with the definition and impl configs
        h.config_from_ptc_def(hcfg, icfg)

        h.interfaces['testi'] = DummyInterface('testi', h, h.bridges['br0'])

        h.create()

        self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'test'))

        h.boot()

        h.net_up()
        h.net_finalize()

        self.assertTrue(h.cli.grep_cmd('ip l', 'testi'))  # Dummy interface
        self.assertTrue(h.cli.grep_cmd('brctl show', 'br0'))

        h.net_down()

        h.shutdown()

        self.assertFalse(h.cli.grep_cmd('brctl show', 'br0'))

        h.remove()

        self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'test'))

    def test_veth_connection_between_two_hosts(self):
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

        h1cfg = HostDef('test1',
                       interfaces={'testi': InterfaceDef('testi', ['192.168.1.1'])})
        i1cfg = ImplementationDef('test', 'RootHost')

        h2cfg = HostDef('test2',
                       interfaces={'testp': InterfaceDef('testp', ['192.168.1.3'])})
        i2cfg = ImplementationDef('test', 'NetNSHost')

        # Host should act the same regardless of using NS or base OS
        h1 = RootHost(h1cfg.name, ptm)
        h2 = NetNSHost(h2cfg.name, ptm)
        log = lm.add_file_logger('test.log', 'test')
        h1.set_logger(log)
        h2.set_logger(log)

        # Now configure the host with the definition and impl configs
        h1.config_from_ptc_def(h1cfg, i1cfg)
        h2.config_from_ptc_def(h2cfg, i2cfg)

        h1.link_interface(h1.interfaces['testi'], h2, h2.interfaces['testp'])

        h1.create()
        h2.create()
        h1.boot()
        h2.boot()
        h1.net_up()
        h2.net_up()
        h1.net_finalize()
        h2.net_finalize()

        self.assertTrue(h1.cli.grep_cmd('ip l', 'testi'))  # Linked interface should start and get peered
        self.assertTrue(h2.cli.grep_cmd('ip l', 'testp'))  # Linked interface should start and get peered

        self.assertTrue(h1.cli.grep_cmd('ip a | grep testi', '192.168.1.1'))
        self.assertTrue(h2.cli.grep_cmd('ip a | grep testp', '192.168.1.3'))

        h1.net_down()
        h2.net_down()

        h2.shutdown()
        h2.remove()

        self.assertFalse(h1.cli.grep_cmd('ip netns', 'test2'))

        h1.shutdown()
        h1.remove()

    #def test_send_packet(self):
        #h1.send_packet('eth0', 'icmp', '10.0.1.3')
        #self.assertEqual(True, False)

    #def test_connect_iface_to_port(self):
        #self.assertEqual(True, False)

    def tearDown(self):
        LinuxCLI().cmd('ip netns del test')
        LinuxCLI().cmd('ip netns del test2')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(NetNSHostTest)
