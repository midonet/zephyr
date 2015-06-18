__author__ = 'micucci'

import unittest
import json
from common.IP import IP
from PTM.PhysicalTopologyConfig import *

class PhysicalTopologyConfigTest(unittest.TestCase):
    def test_read_ip(self):
        cfg = {'ip': '1.1.1.1', 'subnet': '8'}
        ip = IP.make_ip(cfg)
        self.assertEquals(ip.ip, '1.1.1.1')
        self.assertEquals(ip.subnet, '8')

        cfg2 = {'ip': '2.1.1.1'}
        ip2 = IP.make_ip(cfg2)
        self.assertEquals(ip2.ip, '2.1.1.1')
        self.assertEquals(ip2.subnet, '24')

        cfg3 = {'subnet': '24'}
        try:
            ip3 = IP.make_ip(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_bridge(self):
        cfg = {'name': 'br0', 'ip_addresses': [{'ip': '1.1.1.1'}], 'options': 'stp'}
        br = BridgeDef.make_bridge(cfg)
        self.assertEquals(br.name, 'br0')
        self.assertEquals(br.ip_addresses[0].ip, '1.1.1.1')
        self.assertEquals(br.options, ['stp'])

        cfg2 = {'name': 'br0'}
        br2 = BridgeDef.make_bridge(cfg2)
        self.assertEquals(br2.name, 'br0')
        self.assertEquals(len(br2.ip_addresses), 0)
        self.assertEquals(br2.options, None)

        cfg3 = {'ip_addresses': [{'ip': '1.1.1.1'}], 'options': 'stp'}
        try:
            br3 = BridgeDef.make_bridge(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_interface(self):
        cfg = {'name': 'eth0', 'ip_addresses': [{'ip': '1.1.1.1'}],
               'mac_address': '00:00:00:aa:bb:cc', 'vlans': [{ 'id': '1', 'ip_addresses': [{'ip': '10.0.0.2'}]}],
               'linked_bridge': 'br0'}
        iface = InterfaceDef.make_interface(cfg)
        self.assertEquals(iface.name, 'eth0')
        self.assertEquals(iface.ip_addresses[0].ip, '1.1.1.1')
        self.assertEquals(iface.mac_address, '00:00:00:aa:bb:cc')
        self.assertEquals(iface.linked_bridge, 'br0')
        self.assertTrue('1' in iface.vlans)
        self.assertEquals(iface.vlans['1'][0].ip, '10.0.0.2')

        cfg2 = {'name': 'eth0'}
        iface2 = InterfaceDef.make_interface(cfg2)
        self.assertEquals(iface2.name, 'eth0')
        self.assertEquals(len(iface2.ip_addresses), 0)
        self.assertEquals(iface2.mac_address, None)
        self.assertEquals(iface2.linked_bridge, None)
        self.assertEquals(len(iface2.vlans), 0)

        cfg3 = {'ip_addresses': [{'ip': '1.1.1.1'}],
               'mac_address': '00:00:00:aa:bb:cc', 'vlan_id': '1', 'linked_bridge': 'br0'}
        try:
            iface3 = InterfaceDef.make_interface(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_host(self):
        cfg = {'name': 'host1',
               'interfaces': [
                   {'name': 'eth0',
                    'ip_addresses': [{'ip': '1.1.1.1'}]}],
               'bridges': [
                   {'name': 'br0',
                    'ip_addresses': [{'ip': '2.2.2.2'}]}]}

        host = HostDef.make_host(cfg)
        self.assertEquals(host.name, 'host1')
        self.assertTrue('eth0' in host.interfaces)
        self.assertEquals(host.interfaces['eth0'].name, 'eth0')
        self.assertEquals(host.interfaces['eth0'].ip_addresses[0].ip, '1.1.1.1')
        self.assertEquals(len(host.bridges), 1)
        self.assertTrue('br0' in host.bridges)
        self.assertEquals(host.bridges['br0'].ip_addresses[0].ip, '2.2.2.2')

        cfg2 = {'name': 'host2'}

        host2 = HostDef.make_host(cfg2)
        self.assertEquals(host2.name, 'host2')
        self.assertEquals(len(host2.interfaces), 0)
        self.assertEquals(len(host2.bridges), 0)

        cfg3 = {'interfaces': [
                    {'name': 'eth0',
                     'ip_addresses': [{'ip': '1.1.1.1'}]}],
                'bridges': [
                    {'name': 'br0',
                     'ip_addresses': [{'ip': '2.2.2.2'}]}]}
        try:
            iface3 = HostDef.make_host(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_wiring(self):
        cfg = {'near': {'host': 'host1', 'interface': 'eth0'},
               'far':  {'host': 'host2', 'interface': 'eth0'}}

        w = WiringDef.make_wiring(cfg)
        self.assertEquals(w.near.host, 'host1')
        self.assertEquals(w.near.interface, 'eth0')
        self.assertEquals(w.far.host, 'host2')
        self.assertEquals(w.far.interface, 'eth0')

        cfg3 = {'far':  {'host': 'host2', 'interface': 'eth0'}}
        try:
            w3 = WiringDef.make_wiring(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_implementation(self):
        cfg = {'host': 'host1', 'impl': 'Impl', 'arg1': 'foo', 'arg2': 'bar'}
        imp = ImplementationDef.make_implementation(cfg)
        self.assertEquals(imp.host, 'host1')
        self.assertEquals(imp.impl, 'Impl')
        self.assertEquals(imp.kwargs['arg1'], 'foo')
        self.assertEquals(imp.kwargs['arg2'], 'bar')

        cfg2 = {'host': 'host1', 'impl': 'Impl'}
        imp2 = ImplementationDef.make_implementation(cfg2)
        self.assertEquals(imp2.host, 'host1')
        self.assertEquals(imp2.impl, 'Impl')
        self.assertEquals(len(imp2.kwargs), 0)

        cfg3 = {'host': 'host1'}
        try:
            imp3 = ImplementationDef.make_implementation(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_ptc(self):
        with open('test-config.json', 'r') as f:
            cfg = json.load(f)
            ptc = PhysicalTopologyConfig.make_physical_topology(cfg)

        self.assertTrue('root' in ptc.hosts)
        self.assertTrue('zoo1eth0' in ptc.hosts['root'].interfaces)
        self.assertTrue('zoo1' in ptc.hosts)
        self.assertTrue('eth0' in ptc.hosts['zoo1'].interfaces)
        self.assertTrue('cass1' in ptc.hosts)
        self.assertTrue('cmp1' in ptc.hosts)
        self.assertTrue('root' in ptc.implementation)
        self.assertTrue(ptc.implementation['root'].impl == 'RootHost')
        self.assertTrue('zoo1' in ptc.implementation)
        self.assertTrue(ptc.implementation['zoo1'].impl == 'ZookeeperHost')
        self.assertTrue(len(ptc.wiring) > 0)
        self.assertEquals(ptc.wiring['root']['zoo1eth0'].host, 'zoo1')
        self.assertEquals(ptc.wiring['root']['zoo1eth0'].interface, 'eth0')
        self.assertEquals(ptc.wiring['edge1']['eth0'].host, 'cmp1')
        self.assertEquals(ptc.wiring['edge1']['eth0'].interface, 'eth1')

        self.assertTrue('root' in ptc.host_start_order[0])
        self.assertTrue('external1' in ptc.host_start_order[1])
        self.assertTrue('test-host1' in ptc.host_start_order[2])
        self.assertTrue('test-host2' in ptc.host_start_order[3])
        self.assertTrue('zoo1' in ptc.host_start_order[4])
        self.assertTrue('cass1' in ptc.host_start_order[5])
        self.assertTrue('cmp1' in ptc.host_start_order[6])
        self.assertTrue('edge1' in ptc.host_start_order[7])
        
if __name__ == '__main__':
    unittest.main()
