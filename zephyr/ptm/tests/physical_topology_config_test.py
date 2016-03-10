# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import unittest

from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.ip import IP
from zephyr.common.utils import run_unit_test
from zephyr.ptm.physical_topology_config import ApplicationDef
from zephyr.ptm.physical_topology_config import BridgeDef
from zephyr.ptm.physical_topology_config import HostDef
from zephyr.ptm.physical_topology_config import ImplementationDef
from zephyr.ptm.physical_topology_config import InterfaceDef
from zephyr.ptm.physical_topology_config import IPForwardRuleDef
from zephyr.ptm.physical_topology_config import PhysicalTopologyConfig
from zephyr.ptm.physical_topology_config import RouteRuleDef
from zephyr.ptm.physical_topology_config import WiringDef


class PhysicalTopologyConfigTest(unittest.TestCase):
    def test_read_ip(self):
        cfg = {'ip': '1.1.1.1', 'subnet': '8'}
        ip = IP(**cfg)
        self.assertEqual(ip.ip, '1.1.1.1')
        self.assertEqual(ip.subnet, '8')

        cfg2 = {'ip': '2.1.1.1'}
        ip2 = IP(**cfg2)
        self.assertEqual(ip2.ip, '2.1.1.1')
        self.assertEqual(ip2.subnet, '24')

        cfg3 = {'subnet': '24'}
        ip3 = IP(**cfg3)
        self.assertEqual(ip3.ip, '0.0.0.0')
        self.assertEqual(ip3.subnet, '24')

    def test_read_bridge(self):
        cfg = {'name': 'br0', 'ip_addresses': [{'ip': '1.1.1.1'}],
               'options': 'stp'}
        br = BridgeDef.make_bridge(cfg)
        self.assertEqual(br.name, 'br0')
        self.assertEqual(br.ip_addresses[0].ip, '1.1.1.1')
        self.assertEqual(br.options, ['stp'])

        cfg2 = {'name': 'br0'}
        br2 = BridgeDef.make_bridge(cfg2)
        self.assertEqual(br2.name, 'br0')
        self.assertEqual(len(br2.ip_addresses), 0)
        self.assertEqual(br2.options, None)

        cfg3 = {'ip_addresses': [{'ip': '1.1.1.1'}], 'options': 'stp'}
        try:
            BridgeDef.make_bridge(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_interface(self):
        cfg = {'name': 'eth0', 'ip_addresses': [{'ip': '1.1.1.1'}],
               'mac_address': '00:00:00:aa:bb:cc',
               'vlans': [{'id': '1', 'ip_addresses': [{'ip': '10.0.0.2'}]}],
               'linked_bridge': 'br0'}
        iface = InterfaceDef.make_interface(cfg)
        self.assertEqual(iface.name, 'eth0')
        self.assertEqual(iface.ip_addresses[0].ip, '1.1.1.1')
        self.assertEqual(iface.mac_address, '00:00:00:aa:bb:cc')
        self.assertEqual(iface.linked_bridge, 'br0')
        self.assertTrue('1' in iface.vlans)
        self.assertEqual(iface.vlans['1'][0].ip, '10.0.0.2')

        cfg2 = {'name': 'eth0'}
        iface2 = InterfaceDef.make_interface(cfg2)
        self.assertEqual(iface2.name, 'eth0')
        self.assertEqual(len(iface2.ip_addresses), 0)
        self.assertEqual(iface2.mac_address, None)
        self.assertEqual(iface2.linked_bridge, None)
        self.assertEqual(len(iface2.vlans), 0)

        cfg3 = {'ip_addresses': [{'ip': '1.1.1.1'}],
                'mac_address': '00:00:00:aa:bb:cc',
                'vlan_id': '1', 'linked_bridge': 'br0'}
        try:
            InterfaceDef.make_interface(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_ip_rule(self):
        cfg1 = {'exterior': 'eth0', 'interior': 'eth1'}
        r1 = IPForwardRuleDef.make_ip_forward_rule(cfg1)
        self.assertEqual(r1.exterior, 'eth0')
        self.assertEqual(r1.interior, 'eth1')

        cfg2 = {'exterior': 'eth0'}
        try:
            IPForwardRuleDef.make_ip_forward_rule(cfg2)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

        cfg3 = {'interior': 'eth0'}
        try:
            IPForwardRuleDef.make_ip_forward_rule(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_route_rule(self):
        cfg1 = {'dest': 'default', 'gw': '1.1.1.1'}
        r1 = RouteRuleDef.make_route_rule(cfg1)
        self.assertEqual(str(r1.dest), '0.0.0.0/0')
        self.assertEqual(r1.gw.ip, '1.1.1.1')
        self.assertIsNone(r1.dev)

        cfg2 = {'dest': '2.2.2.2/24', 'dev': 'eth0'}
        r2 = RouteRuleDef.make_route_rule(cfg2)
        self.assertEqual(str(r2.dest), '2.2.2.2/24')
        self.assertIsNone(r2.gw)
        self.assertEqual(r2.dev, 'eth0')

        cfg3 = {'gw': '1.1.1.1'}
        try:
            RouteRuleDef.make_route_rule(cfg3)
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
                    'ip_addresses': [{'ip': '2.2.2.2'}]}],
               'ip_forward': [
                   {'exterior': 'eth0', 'interior': 'eth1'}],
               'routes': [
                   {'dest': 'default', 'gw': '3.3.3.3', 'dev': 'eth2'}]}

        host = HostDef.make_host(cfg)
        self.assertEqual(host.name, 'host1')
        self.assertTrue('eth0' in host.interfaces)
        self.assertEqual(host.interfaces['eth0'].name, 'eth0')
        self.assertEqual(host.interfaces['eth0'].ip_addresses[0].ip, '1.1.1.1')
        self.assertEqual(len(host.bridges), 1)
        self.assertTrue('br0' in host.bridges)
        self.assertEqual(host.bridges['br0'].ip_addresses[0].ip, '2.2.2.2')
        self.assertEqual(len(host.ip_forward_rules), 1)
        self.assertEqual(host.ip_forward_rules[0].exterior, 'eth0')
        self.assertEqual(host.ip_forward_rules[0].interior, 'eth1')
        self.assertEqual(len(host.route_rules), 1)
        self.assertEqual(str(host.route_rules[0].dest), '0.0.0.0/0')
        self.assertEqual(host.route_rules[0].gw.ip, '3.3.3.3')
        self.assertEqual(host.route_rules[0].dev, 'eth2')

        cfg2 = {'name': 'host2'}

        host2 = HostDef.make_host(cfg2)
        self.assertEqual(host2.name, 'host2')
        self.assertEqual(len(host2.interfaces), 0)
        self.assertEqual(len(host2.bridges), 0)
        self.assertEqual(len(host2.ip_forward_rules), 0)

        cfg3 = {'interfaces': [
            {'name': 'eth0',
             'ip_addresses': [{'ip': '1.1.1.1'}]}],
            'bridges': [
                {'name': 'br0',
                 'ip_addresses': [{'ip': '2.2.2.2'}]}],
            'ip_forward': [
                {'exterior': 'eth0', 'interior': 'eth1'}]}
        try:
            HostDef.make_host(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_wiring(self):
        cfg = {'near': {'host': 'host1', 'interface': 'eth0'},
               'far': {'host': 'host2', 'interface': 'eth0'}}

        w = WiringDef.make_wiring(cfg)
        self.assertEqual(w.near.host, 'host1')
        self.assertEqual(w.near.interface, 'eth0')
        self.assertEqual(w.far.host, 'host2')
        self.assertEqual(w.far.interface, 'eth0')

        cfg3 = {'far': {'host': 'host2', 'interface': 'eth0'}}
        try:
            WiringDef.make_wiring(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_application(self):
        cfg = {'class': 'Impl', 'arg1': 'foo', 'arg2': 'bar'}
        imp = ApplicationDef.make_application(cfg)
        self.assertEqual(imp.class_name, 'Impl')
        self.assertEqual(imp.kwargs['arg1'], 'foo')
        self.assertEqual(imp.kwargs['arg2'], 'bar')

        cfg2 = {'class': 'Impl'}
        imp2 = ApplicationDef.make_application(cfg2)
        self.assertEqual(imp2.class_name, 'Impl')
        self.assertEqual(0, len(imp2.kwargs))

        cfg3 = {'arg1': 'bar'}
        try:
            ApplicationDef.make_application(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_implementation(self):
        cfg = {'host': 'host1', 'impl': 'Impl',
               'apps': [{'class': 'App', 'arg1': 'foo', 'arg2': 'bar'}]}
        imp = ImplementationDef.make_implementation(cfg)
        self.assertEqual(imp.host, 'host1')
        self.assertEqual(imp.impl, 'Impl')
        self.assertEqual(len(imp.apps), 1)
        self.assertEqual('App', imp.apps[0].class_name)
        self.assertEqual('bar', imp.apps[0].kwargs['arg2'])

        cfg2 = {'host': 'host1', 'impl': 'Impl', 'apps': []}
        imp2 = ImplementationDef.make_implementation(cfg2)
        self.assertEqual(imp2.host, 'host1')
        self.assertEqual(imp2.impl, 'Impl')
        self.assertEqual(len(imp2.apps), 0)

        cfg3 = {'host': 'host1'}
        try:
            ImplementationDef.make_implementation(cfg3)
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Omitting required field should throw')

    def test_read_ptc(self):
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)

        with open(dir_path + '/test-config.json', 'r') as f:
            cfg = json.load(f)
            ptc = PhysicalTopologyConfig.make_physical_topology(cfg)

        self.assertTrue('root' in ptc.hosts)
        self.assertTrue('zoo1eth0' in ptc.hosts['root'].interfaces)
        self.assertTrue('zoo1' in ptc.hosts)
        self.assertTrue('eth0' in ptc.hosts['zoo1'].interfaces)
        self.assertTrue('cmp1' in ptc.hosts)
        self.assertTrue('root' in ptc.implementation)
        self.assertEqual(ptc.implementation['root'].impl,
                         'ptm.host.RootHost')
        self.assertEqual(0, len(ptc.implementation['root'].apps))
        self.assertTrue('zoo1' in ptc.implementation)
        self.assertEqual(ptc.implementation['zoo1'].impl,
                         'ptm.host.IPNetNSHost')
        self.assertTrue(1, len(ptc.implementation['zoo1'].apps))
        self.assertEqual(ptc.implementation['zoo1'].apps[0].class_name,
                         'ptm.application.Zookeeper')
        self.assertGreater(len(ptc.wiring), 0)
        self.assertEqual(ptc.wiring['root']['zoo1eth0'].host, 'zoo1')
        self.assertEqual(ptc.wiring['root']['zoo1eth0'].interface, 'eth0')
        self.assertEqual(ptc.wiring['edge1']['eth0'].host, 'cmp1')
        self.assertEqual(ptc.wiring['edge1']['eth0'].interface, 'eth1')

        self.assertTrue('root' in ptc.host_start_order)
        self.assertTrue('external1' in ptc.host_start_order)
        self.assertTrue('test-host1' in ptc.host_start_order[2])
        self.assertTrue('test-host2' in ptc.host_start_order[2])
        self.assertTrue('zoo1' in ptc.host_start_order)
        self.assertTrue('cmp1' in ptc.host_start_order)
        self.assertTrue('edge1' in ptc.host_start_order[3])


run_unit_test(PhysicalTopologyConfigTest)
