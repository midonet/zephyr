__author__ = 'micucci'

from PTM.MNRootServer import MNRootServer
from PTM.MapConfigReader import MapConfigReader
from PTM.PhysicalTopologyConfig import *
import unittest
import json
from common.CLI import LinuxCLI

class RootServerUnitTest(unittest.TestCase):

    def test_server_init(self):
        test_server1 = MNRootServer()
        test_server1.init()

        self.assertEqual(len(test_server1.network_hosts), 1)
        self.assertEqual(test_server1.network_hosts[0].name, 'net-node')

    def test_server_init_sets_up_zk_and_cass_ips(self):
        test_server1 = MNRootServer()
        test_server1.config_compute(HostDef('cmp1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                  [IPDef('10.0.0.8')])]))
        test_server1.config_compute(HostDef('cmp2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                  [IPDef('10.0.0.9')])]))

        test_server1.config_zookeeper(HostDef('zoo1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.2')])]))

        test_server1.config_cassandra(HostDef('cass1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.5')])],
                                              options='56713727820156410577229101238628035242'))
        test_server1.config_cassandra(HostDef('cass2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.6')])],
                                              options='113427455640312821154458202477256070484'))
        test_server1.config_cassandra(HostDef('cass3', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.7')])],
                                              options='170141183460469231731687303715884105726'))

        test_server1.init()

        self.assertEqual(len(test_server1.network_hosts), 1)
        self.assertEqual(test_server1.network_hosts[0].name, 'net-node')
        self.assertEqual(len(test_server1.network_hosts[0].zookeeper_ips), 1)

        self.assertEqual(len(test_server1.zookeeper_hosts), 1)
        self.assertEqual(len(test_server1.zookeeper_ips), 1)

        self.assertEqual(len(test_server1.cassandra_hosts), 3)
        self.assertEqual(len(test_server1.cassandra_ips), 3)

        self.assertEqual(test_server1.zookeeper_ips[0].ip_address, '10.0.0.2')

        self.assertEqual(test_server1.cassandra_ips[0].ip_address, '10.0.0.5')
        self.assertEqual(test_server1.cassandra_ips[1].ip_address, '10.0.0.6')
        self.assertEqual(test_server1.cassandra_ips[2].ip_address, '10.0.0.7')

        self.assertEqual(test_server1.cassandra_hosts[0].cassandra_ips[0],
                         test_server1.cassandra_ips[0])
        self.assertEqual(test_server1.cassandra_hosts[1].cassandra_ips[1],
                         test_server1.cassandra_ips[1])
        self.assertEqual(test_server1.cassandra_hosts[2].cassandra_ips[2],
                         test_server1.cassandra_ips[2])

        self.assertEqual(test_server1.zookeeper_hosts[0].zookeeper_ips[0],
                         test_server1.zookeeper_ips[0])

        self.assertEqual(test_server1.compute_hosts[0].cassandra_ips[0],
                         test_server1.cassandra_ips[0])
        self.assertEqual(test_server1.compute_hosts[0].cassandra_ips[1],
                         test_server1.cassandra_ips[1])
        self.assertEqual(test_server1.compute_hosts[0].cassandra_ips[2],
                         test_server1.cassandra_ips[2])

        self.assertEqual(test_server1.compute_hosts[1].cassandra_ips[0],
                         test_server1.cassandra_ips[0])
        self.assertEqual(test_server1.compute_hosts[1].cassandra_ips[1],
                         test_server1.cassandra_ips[1])
        self.assertEqual(test_server1.compute_hosts[1].cassandra_ips[2],
                         test_server1.cassandra_ips[2])

        self.assertEqual(test_server1.compute_hosts[0].zookeeper_ips[0],
                         test_server1.zookeeper_ips[0])
        self.assertEqual(test_server1.compute_hosts[1].zookeeper_ips[0],
                         test_server1.zookeeper_ips[0])

    def test_config_bridge(self):
        test_server1 = MNRootServer()
        test_server1.config_bridge(BridgeDef(name='br0', ip_list=[IPDef('10.0.0.240', '16')]))
        test_server1.config_bridge(BridgeDef(name='brv0', options='stp'))
        self.assertEqual(len(test_server1.bridges), 2)
        self.assertTrue('br0' in test_server1.bridges)
        self.assertTrue('brv0' in test_server1.bridges)

        self.assertEqual(test_server1.bridges['br0'].name, 'br0')
        self.assertEqual(test_server1.bridges['brv0'].name, 'brv0')

        self.assertEqual(len(test_server1.bridges['br0'].options), 0)
        self.assertEqual(len(test_server1.bridges['brv0'].options), 1)
        self.assertEqual(test_server1.bridges['brv0'].options[0], 'stp')

        self.assertEqual(len(test_server1.bridges['br0'].ip_list), 1)
        self.assertEqual(len(test_server1.bridges['brv0'].ip_list), 0)

        self.assertIs(test_server1.bridges['br0'].near_host, test_server1)
        self.assertIs(test_server1.bridges['brv0'].near_host, test_server1)

    def test_config_zookeeper(self):
        test_server1 = MNRootServer()
        test_server1.config_bridge(BridgeDef(name='br0', ip_list=[IPDef('10.0.0.240', '16')]))
        test_server1.config_zookeeper(HostDef('zoo1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.2')])]))
        test_server1.config_zookeeper(HostDef('zoo2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.3')])]))
        test_server1.config_zookeeper(HostDef('zoo3', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.4')])]))

        test_server1.init()

        self.assertEqual(len(test_server1.zookeeper_hosts), 3)
        self.assertEqual(len(test_server1.zookeeper_ips), 3)

        self.assertEqual(test_server1.zookeeper_hosts[0].name, 'zoo1')
        self.assertEqual(test_server1.zookeeper_hosts[1].name, 'zoo2')
        self.assertEqual(test_server1.zookeeper_hosts[2].name, 'zoo3')

        self.assertEqual(test_server1.zookeeper_hosts[0].num_id, '1')
        self.assertEqual(test_server1.zookeeper_hosts[1].num_id, '2')
        self.assertEqual(test_server1.zookeeper_hosts[2].num_id, '3')

        self.assertEqual(test_server1.zookeeper_hosts[0].ip, test_server1.zookeeper_ips[0])
        self.assertEqual(test_server1.zookeeper_hosts[1].ip, test_server1.zookeeper_ips[1])
        self.assertEqual(test_server1.zookeeper_hosts[2].ip, test_server1.zookeeper_ips[2])

        self.assertEqual(test_server1.zookeeper_hosts[0].zookeeper_ips[0], test_server1.zookeeper_ips[0])
        self.assertEqual(test_server1.zookeeper_hosts[1].ip, test_server1.zookeeper_ips[1])
        self.assertEqual(test_server1.zookeeper_hosts[2].ip, test_server1.zookeeper_ips[2])

        self.assertEqual(len(test_server1.zookeeper_hosts[0].bridges), 0)
        self.assertEqual(len(test_server1.zookeeper_hosts[1].bridges), 0)
        self.assertEqual(len(test_server1.zookeeper_hosts[2].bridges), 0)

        self.assertTrue('zoo1' in test_server1.interfaces_for_host)
        self.assertTrue('zoo2' in test_server1.interfaces_for_host)
        self.assertTrue('zoo3' in test_server1.interfaces_for_host)

        self.assertTrue('eth0' in test_server1.interfaces_for_host['zoo1'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['zoo2'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['zoo3'])

        test_if1 = test_server1.interfaces_for_host['zoo1']['eth0']
        test_if2 = test_server1.interfaces_for_host['zoo2']['eth0']
        test_if3 = test_server1.interfaces_for_host['zoo3']['eth0']

        self.assertEqual(test_if1.name, 'vzoo1eth0')
        self.assertEqual(test_if1.peer_name, 'vzoo1eth0.p')
        self.assertTrue(test_if1.far_host is not None)
        self.assertEqual(test_if1.far_host.name, 'zoo1')
        self.assertEqual(test_if1.far_iface_name, 'eth0')
        self.assertEqual(test_if1.mac, 'default')
        self.assertTrue(test_if1.linked_bridge is not None)
        self.assertEqual(test_if1.linked_bridge.name, 'br0')
        self.assertTrue(test_if1.linked_bridge.near_host is not None)
        self.assertIs(test_if1.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if1.ip_list), 1)
        self.assertEqual(test_if1.ip_list[0].ip_address, '10.0.0.2')
        self.assertEqual(test_if1.ip_list[0].subnet_mask, '24')

        self.assertEqual(test_if2.name, 'vzoo2eth0')
        self.assertEqual(test_if2.peer_name, 'vzoo2eth0.p')
        self.assertTrue(test_if2.far_host is not None)
        self.assertEqual(test_if2.far_host.name, 'zoo2')
        self.assertEqual(test_if2.far_iface_name, 'eth0')
        self.assertEqual(test_if2.mac, 'default')
        self.assertTrue(test_if2.linked_bridge is not None)
        self.assertEqual(test_if2.linked_bridge.name, 'br0')
        self.assertTrue(test_if2.linked_bridge.near_host is not None)
        self.assertIs(test_if2.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if2.ip_list), 1)
        self.assertEqual(test_if2.ip_list[0].ip_address, '10.0.0.3')
        self.assertEqual(test_if2.ip_list[0].subnet_mask, '24')

        self.assertEqual(test_if3.name, 'vzoo3eth0')
        self.assertEqual(test_if3.peer_name, 'vzoo3eth0.p')
        self.assertTrue(test_if3.far_host is not None)
        self.assertEqual(test_if3.far_host.name, 'zoo3')
        self.assertEqual(test_if3.far_iface_name, 'eth0')
        self.assertEqual(test_if3.mac, 'default')
        self.assertTrue(test_if3.linked_bridge is not None)
        self.assertEqual(test_if3.linked_bridge.name, 'br0')
        self.assertTrue(test_if3.linked_bridge.near_host is not None)
        self.assertIs(test_if3.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if3.ip_list), 1)
        self.assertEqual(test_if3.ip_list[0].ip_address, '10.0.0.4')
        self.assertEqual(test_if3.ip_list[0].subnet_mask, '24')

    def test_config_cassandra(self):
        test_server1 = MNRootServer()

        test_server1.config_bridge(BridgeDef(name='br0', ip_list=[IPDef('10.0.0.240', '16')]))
        test_server1.config_cassandra(HostDef('cass1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.5')])],
                                              options='56713727820156410577229101238628035242'))
        test_server1.config_cassandra(HostDef('cass2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.6')])],
                                              options='113427455640312821154458202477256070484'))
        test_server1.config_cassandra(HostDef('cass3', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                     [IPDef('10.0.0.7')])],
                                              options='170141183460469231731687303715884105726'))
        test_server1.init()
        
        self.assertEqual(len(test_server1.cassandra_hosts), 3)
        self.assertEqual(len(test_server1.cassandra_ips), 3)

        self.assertEqual(test_server1.cassandra_hosts[0].name, 'cass1')
        self.assertEqual(test_server1.cassandra_hosts[1].name, 'cass2')
        self.assertEqual(test_server1.cassandra_hosts[2].name, 'cass3')

        self.assertEqual(test_server1.cassandra_hosts[0].init_token, '56713727820156410577229101238628035242')
        self.assertEqual(test_server1.cassandra_hosts[1].init_token, '113427455640312821154458202477256070484')
        self.assertEqual(test_server1.cassandra_hosts[2].init_token, '170141183460469231731687303715884105726')

        self.assertEqual(test_server1.cassandra_hosts[0].num_id, '1')
        self.assertEqual(test_server1.cassandra_hosts[1].num_id, '2')
        self.assertEqual(test_server1.cassandra_hosts[2].num_id, '3')

        self.assertEqual(test_server1.cassandra_hosts[0].ip, test_server1.cassandra_ips[0])
        self.assertEqual(test_server1.cassandra_hosts[1].ip, test_server1.cassandra_ips[1])
        self.assertEqual(test_server1.cassandra_hosts[2].ip, test_server1.cassandra_ips[2])

        self.assertEqual(test_server1.cassandra_hosts[0].cassandra_ips[0], test_server1.cassandra_ips[0])
        self.assertEqual(test_server1.cassandra_hosts[1].ip, test_server1.cassandra_ips[1])
        self.assertEqual(test_server1.cassandra_hosts[2].ip, test_server1.cassandra_ips[2])

        self.assertEqual(len(test_server1.cassandra_hosts[0].bridges), 0)
        self.assertEqual(len(test_server1.cassandra_hosts[1].bridges), 0)
        self.assertEqual(len(test_server1.cassandra_hosts[2].bridges), 0)

        self.assertTrue('cass1' in test_server1.interfaces_for_host)
        self.assertTrue('cass2' in test_server1.interfaces_for_host)
        self.assertTrue('cass3' in test_server1.interfaces_for_host)

        self.assertTrue('eth0' in test_server1.interfaces_for_host['cass1'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['cass2'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['cass3'])

        test_if1 = test_server1.interfaces_for_host['cass1']['eth0']
        test_if2 = test_server1.interfaces_for_host['cass2']['eth0']
        test_if3 = test_server1.interfaces_for_host['cass3']['eth0']

        self.assertEqual(test_if1.name, 'vcass1eth0')
        self.assertEqual(test_if1.peer_name, 'vcass1eth0.p')
        self.assertTrue(test_if1.far_host is not None)
        self.assertEqual(test_if1.far_host.name, 'cass1')
        self.assertEqual(test_if1.far_iface_name, 'eth0')
        self.assertEqual(test_if1.mac, 'default')
        self.assertTrue(test_if1.linked_bridge is not None)
        self.assertEqual(test_if1.linked_bridge.name, 'br0')
        self.assertTrue(test_if1.linked_bridge.near_host is not None)
        self.assertIs(test_if1.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if1.ip_list), 1)
        self.assertEqual(test_if1.ip_list[0].ip_address, '10.0.0.5')
        self.assertEqual(test_if1.ip_list[0].subnet_mask, '24')

        self.assertEqual(test_if2.name, 'vcass2eth0')
        self.assertEqual(test_if2.peer_name, 'vcass2eth0.p')
        self.assertTrue(test_if2.far_host is not None)
        self.assertEqual(test_if2.far_host.name, 'cass2')
        self.assertEqual(test_if2.far_iface_name, 'eth0')
        self.assertEqual(test_if2.mac, 'default')
        self.assertTrue(test_if2.linked_bridge is not None)
        self.assertEqual(test_if2.linked_bridge.name, 'br0')
        self.assertTrue(test_if2.linked_bridge.near_host is not None)
        self.assertIs(test_if2.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if2.ip_list), 1)
        self.assertEqual(test_if2.ip_list[0].ip_address, '10.0.0.6')
        self.assertEqual(test_if2.ip_list[0].subnet_mask, '24')

        self.assertEqual(test_if3.name, 'vcass3eth0')
        self.assertEqual(test_if3.peer_name, 'vcass3eth0.p')
        self.assertTrue(test_if3.far_host is not None)
        self.assertEqual(test_if3.far_host.name, 'cass3')
        self.assertEqual(test_if3.far_iface_name, 'eth0')
        self.assertEqual(test_if3.mac, 'default')
        self.assertTrue(test_if3.linked_bridge is not None)
        self.assertEqual(test_if3.linked_bridge.name, 'br0')
        self.assertTrue(test_if3.linked_bridge.near_host is not None)
        self.assertIs(test_if3.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if3.ip_list), 1)
        self.assertEqual(test_if3.ip_list[0].ip_address, '10.0.0.7')
        self.assertEqual(test_if3.ip_list[0].subnet_mask, '24')
        
    def test_config_compute(self):
        test_server1 = MNRootServer()

        test_server1.config_bridge(BridgeDef(name='br0', ip_list=[IPDef('10.0.0.240', '16')]))
        test_server1.config_compute(HostDef('cmp1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.8')])]))
        test_server1.config_compute(HostDef('cmp2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.9')])]))
        test_server1.config_compute(HostDef('cmp3', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                    [IPDef('10.0.0.10')])]))

        test_server1.init()

        self.assertEqual(len(test_server1.compute_hosts), 3)
    
        self.assertEqual(test_server1.compute_hosts[0].name, 'cmp1')
        self.assertEqual(test_server1.compute_hosts[1].name, 'cmp2')
        self.assertEqual(test_server1.compute_hosts[2].name, 'cmp3')
    
        self.assertEqual(test_server1.compute_hosts[0].num_id, '1')
        self.assertEqual(test_server1.compute_hosts[1].num_id, '2')
        self.assertEqual(test_server1.compute_hosts[2].num_id, '3')
    
        self.assertEqual(len(test_server1.compute_hosts[0].bridges), 0)
        self.assertEqual(len(test_server1.compute_hosts[1].bridges), 0)
        self.assertEqual(len(test_server1.compute_hosts[2].bridges), 0)
    
        self.assertTrue('cmp1' in test_server1.interfaces_for_host)
        self.assertTrue('cmp2' in test_server1.interfaces_for_host)
        self.assertTrue('cmp3' in test_server1.interfaces_for_host)
    
        self.assertTrue('eth0' in test_server1.interfaces_for_host['cmp1'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['cmp2'])
        self.assertTrue('eth0' in test_server1.interfaces_for_host['cmp3'])
    
        test_if1 = test_server1.interfaces_for_host['cmp1']['eth0']
        test_if2 = test_server1.interfaces_for_host['cmp2']['eth0']
        test_if3 = test_server1.interfaces_for_host['cmp3']['eth0']
    
        self.assertEqual(test_if1.name, 'vcmp1eth0')
        self.assertEqual(test_if1.peer_name, 'vcmp1eth0.p')
        self.assertTrue(test_if1.far_host is not None)
        self.assertEqual(test_if1.far_host.name, 'cmp1')
        self.assertEqual(test_if1.far_iface_name, 'eth0')
        self.assertEqual(test_if1.mac, 'default')
        self.assertTrue(test_if1.linked_bridge is not None)
        self.assertEqual(test_if1.linked_bridge.name, 'br0')
        self.assertTrue(test_if1.linked_bridge.near_host is not None)
        self.assertIs(test_if1.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if1.ip_list), 1)
        self.assertEqual(test_if1.ip_list[0].ip_address, '10.0.0.8')
        self.assertEqual(test_if1.ip_list[0].subnet_mask, '24')
    
        self.assertEqual(test_if2.name, 'vcmp2eth0')
        self.assertEqual(test_if2.peer_name, 'vcmp2eth0.p')
        self.assertTrue(test_if2.far_host is not None)
        self.assertEqual(test_if2.far_host.name, 'cmp2')
        self.assertEqual(test_if2.far_iface_name, 'eth0')
        self.assertEqual(test_if2.mac, 'default')
        self.assertTrue(test_if2.linked_bridge is not None)
        self.assertEqual(test_if2.linked_bridge.name, 'br0')
        self.assertTrue(test_if2.linked_bridge.near_host is not None)
        self.assertIs(test_if2.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if2.ip_list), 1)
        self.assertEqual(test_if2.ip_list[0].ip_address, '10.0.0.9')
        self.assertEqual(test_if2.ip_list[0].subnet_mask, '24')
    
        self.assertEqual(test_if3.name, 'vcmp3eth0')
        self.assertEqual(test_if3.peer_name, 'vcmp3eth0.p')
        self.assertTrue(test_if3.far_host is not None)
        self.assertEqual(test_if3.far_host.name, 'cmp3')
        self.assertEqual(test_if3.far_iface_name, 'eth0')
        self.assertEqual(test_if3.mac, 'default')
        self.assertTrue(test_if3.linked_bridge is not None)
        self.assertEqual(test_if3.linked_bridge.name, 'br0')
        self.assertTrue(test_if3.linked_bridge.near_host is not None)
        self.assertIs(test_if3.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if3.ip_list), 1)
        self.assertEqual(test_if3.ip_list[0].ip_address, '10.0.0.10')
        self.assertEqual(test_if3.ip_list[0].subnet_mask, '24')

    def test_config_router(self):
        test_server1 = MNRootServer()

        test_server1.config_compute(HostDef('cmp1', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                  [IPDef('10.0.0.8')])]))
        test_server1.config_compute(HostDef('cmp2', [InterfaceDef('eth0', BridgeLinkDef(name='br0'),
                                                                  [IPDef('10.0.0.8')])]))
        test_server1.config_router(RouterDef('quagga',
                                             [PeerInterfaceDef('eth0', 'cmp1',
                                                               InterfaceDef(name='eth1',
                                                                            ip_list=[IPDef('10.0.0.240')])),
                                              PeerInterfaceDef('eth1', 'cmp2',
                                                               InterfaceDef(name='eth1',
                                                                            ip_list=[IPDef('10.0.0.240')]))]))

    def test_config_generic_host(self):
        test_server1 = MNRootServer()

        test_server1.config_bridge(BridgeDef(name='brv0', options='stp'))
        test_server1.config_generic_host(HostDef('v1.1', [InterfaceDef('eth0', BridgeLinkDef(name='brv0')),
                                                          InterfaceDef('eth1', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v1.2', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v2.1', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v2.2', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))

        self.assertEqual(len(test_server1.hosts), 4)

        self.assertTrue('v1.1' in test_server1.hosts)
        self.assertTrue('v1.2' in test_server1.hosts)
        self.assertTrue('v2.1' in test_server1.hosts)
        self.assertTrue('v2.2' in test_server1.hosts)

        self.assertEqual(test_server1.hosts['v1.1'].name, 'v1.1')

        self.assertEqual(len(test_server1.hosts['v1.1'].bridges), 0)
        self.assertTrue('v1.1' in test_server1.interfaces_for_host)

        self.assertTrue('eth0' in test_server1.interfaces_for_host['v1.1'])
        self.assertTrue('eth1' in test_server1.interfaces_for_host['v1.1'])

        test_if1 = test_server1.interfaces_for_host['v1.1']['eth0']
        test_if2 = test_server1.interfaces_for_host['v1.1']['eth1']

        self.assertEqual(test_if1.name, 'vv1.1eth0')
        self.assertEqual(test_if1.peer_name, 'vv1.1eth0.p')
        self.assertTrue(test_if1.far_host is not None)
        self.assertEqual(test_if1.far_host.name, 'v1.1')
        self.assertEqual(test_if1.far_iface_name, 'eth0')
        self.assertEqual(test_if1.mac, 'default')
        self.assertTrue(test_if1.linked_bridge is not None)
        self.assertEqual(test_if1.linked_bridge.name, 'brv0')
        self.assertTrue(test_if1.linked_bridge.near_host is not None)
        self.assertIs(test_if1.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if1.ip_list), 0)

        self.assertEqual(test_if2.name, 'vv1.1eth1')
        self.assertEqual(test_if2.peer_name, 'vv1.1eth1.p')
        self.assertTrue(test_if2.far_host is not None)
        self.assertEqual(test_if2.far_host.name, 'v1.1')
        self.assertEqual(test_if2.far_iface_name, 'eth1')
        self.assertEqual(test_if2.mac, 'default')
        self.assertTrue(test_if2.linked_bridge is not None)
        self.assertEqual(test_if2.linked_bridge.name, 'brv0')
        self.assertTrue(test_if2.linked_bridge.near_host is not None)
        self.assertIs(test_if2.linked_bridge.near_host, test_server1)
        self.assertEqual(len(test_if2.ip_list), 0)

    def test_config_vlan(self):
        test_server1 = MNRootServer()

        test_server1.config_bridge(BridgeDef(name='brv0', options='stp'))
        test_server1.config_generic_host(HostDef('v1.1', [InterfaceDef('eth0', BridgeLinkDef(name='brv0')),
                                                          InterfaceDef('eth1', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v1.2', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v2.1', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))
        test_server1.config_generic_host(HostDef('v2.2', [InterfaceDef('eth0', BridgeLinkDef(name='brv0'))]))
        test_server1.config_vlan(VLANDef(vlan_id='1',
                                         host_list=[HostDef('v1.1',
                                                            [InterfaceDef('eth0', ip_list=[IPDef('172.16.0.224')])]),
                                                    HostDef('v1.1',
                                                            [InterfaceDef('eth1', ip_list=[IPDef('172.16.0.223')])]),
                                                    HostDef('v2.1',
                                                            [InterfaceDef('eth0', ip_list=[IPDef('172.16.0.225')])])]))
        test_server1.config_vlan(VLANDef(vlan_id='2',
                                         host_list=[HostDef('v1.2',
                                                            [InterfaceDef('eth0', ip_list=[IPDef('172.16.0.224')])]),
                                                    HostDef('v2.2',
                                                            [InterfaceDef('eth0', ip_list=[IPDef('172.16.0.225')])])]))

        self.assertEqual(len(test_server1.vlans), 2)

        self.assertEqual(test_server1.vlans[0].vlan_id, '1')
        self.assertEqual(test_server1.vlans[1].vlan_id, '2')

        self.assertEqual(len(test_server1.vlans[0].interfaces), 3)
        self.assertEqual(len(test_server1.vlans[1].interfaces), 2)

        self.assertTrue(test_server1.vlans[0].interfaces[0][0].far_host is not None)
        self.assertTrue(test_server1.vlans[0].interfaces[1][0].far_host is not None)
        self.assertTrue(test_server1.vlans[0].interfaces[2][0].far_host is not None)
        self.assertTrue(test_server1.vlans[1].interfaces[0][0].far_host is not None)
        self.assertTrue(test_server1.vlans[1].interfaces[1][0].far_host is not None)

        self.assertEqual(test_server1.vlans[0].interfaces[0][0].far_host.name, 'v1.1')
        self.assertEqual(test_server1.vlans[0].interfaces[1][0].far_host.name, 'v1.1')
        self.assertEqual(test_server1.vlans[0].interfaces[2][0].far_host.name, 'v2.1')
        self.assertEqual(test_server1.vlans[1].interfaces[0][0].far_host.name, 'v1.2')
        self.assertEqual(test_server1.vlans[1].interfaces[1][0].far_host.name, 'v2.2')

        self.assertEqual(test_server1.vlans[0].interfaces[0][0].far_iface_name, 'eth0')
        self.assertEqual(test_server1.vlans[0].interfaces[1][0].far_iface_name, 'eth1')
        self.assertEqual(test_server1.vlans[0].interfaces[2][0].far_iface_name, 'eth0')
        self.assertEqual(test_server1.vlans[1].interfaces[0][0].far_iface_name, 'eth0')
        self.assertEqual(test_server1.vlans[1].interfaces[1][0].far_iface_name, 'eth0')

    def test_create_test_server_from_json(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        test_server2 = MNRootServer('root', './test-logs')
        test_server2.config_from_physical_topology_config(config)
        test_server2.init()
        self.assertEqual(True, True)

    def test_create_test_server_from_ptc(self):
        ptc = PhysicalTopologyConfig()
        ptc.add_bridge_def(BridgeDef('br0', '', [IPDef('0.0.0.0', '32')], ''))
        ptc.add_compute_def(HostDef('host1',
                                    [InterfaceDef('eth0',
                                                  BridgeLinkDef('', 'br0'),
                                                  [IPDef('1.1.1.1', '32')],
                                                  '')],
                                    ''))
        ptc.add_host_def(HostDef('host1',
                                 [InterfaceDef('eth0',
                                               BridgeLinkDef('', 'br0'),
                                               [IPDef('2.2.2.2', '32')],
                                               '')],
                                 ''))

        test_server = MNRootServer.create_from_physical_topology_config(ptc)
        test_server.init()
        # test_server.prepare_files()
        # test_server.setup()
        # test_server.start()

        # test_server.stop()
        # test_server.cleanup()
        self.assertEqual(True, True)

    def test_get_host_on_server(self):
        test_system = MNRootServer()
        test_system.config_compute(HostDef('cmp1', [InterfaceDef(name='eth0', ip_list=[IPDef('2.2.2.2', '32')])]))
        h = test_system.get_host('cmp1')

        self.assertNotEqual(h, None)

    def test_get_vm_host_on_server(self):
        test_system = MNRootServer()
        test_system.config_compute(HostDef('cmp1', [InterfaceDef(name='eth0', ip_list=[IPDef('2.2.2.2', '32')])]))
        test_system.config_vm(VMDef('cmp1', HostDef('vm1', [InterfaceDef(name='eth0',
                                                                         ip_list=[IPDef('3.3.3.3', '32')])])))

        h = test_system.get_host('cmp1')
        self.assertNotEqual(h, None)

        """ :type: ComputeHost"""
        vm = h.get_vm('vm1')
        self.assertNotEqual(vm, None)

    def test_print_config(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        ts = MNRootServer('root', './test-logs')
        ts.create_from_physical_topology_config(config)
        ts.init()
        ts.print_config()

    def test_create_remove_host(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        ts = MNRootServer('root', './test-logs')
        ts.create_from_physical_topology_config(config)

        ts.create_hosts()

        ts.remove_hosts()

    def test_add_delete_interfaces(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        ts = MNRootServer('root', './test-logs')
        ts.create_from_physical_topology_config(config)

        ts.create_hosts()
        ts.add_interfaces()

        ts.delete_interfaces()
        ts.remove_hosts()

    def test_prepare_files(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        ts = MNRootServer('root', './test-logs')
        ts.create_from_physical_topology_config(config)

        ts.create_hosts()
        ts.add_interfaces()
        ts.prepare_files()

        ts.delete_interfaces()
        ts.remove_hosts()

    def test_full_start_simple(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        ts = MNRootServer('root', './test-logs')
        ts.create_from_physical_topology_config(config)

        ts.startup()
        ts.shutdown()

    def tearDown(self):
        self.clear_test()

    def clear_test(self):
        with open('test-config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        for h in config.zookeeper_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
            for i in h.interface_list:
                LinuxCLI().cmd('ip l del v' + h.name + i.name)
        for h in config.cassandra_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
            for i in h.interface_list:
                LinuxCLI().cmd('ip l del v' + h.name + i.name)
        for h in config.compute_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
            for i in h.interface_list:
                LinuxCLI().cmd('ip l del v' + h.name + i.name)
        for h in config.host_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
            for i in h.interface_list:
                LinuxCLI().cmd('ip l del v' + h.name + i.name)
        for h in config.router_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
            for i in h.peer_interface_list:
                LinuxCLI().cmd('ip l del v' + h.name + i.interface_name)
        for h in config.vm_config:
            LinuxCLI().cmd('ip netns del ' + h.name)
        for b in config.bridge_config:
            LinuxCLI().cmd('ip l set dev ' + b.name + ' down')
            LinuxCLI().cmd('brctl delbr ' + b.name)


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(RootServerUnitTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)
