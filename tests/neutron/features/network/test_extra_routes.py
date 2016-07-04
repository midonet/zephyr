# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import operator
import unittest
from zephyr.common import ip
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm import test_case


class TestExtraRoutes(NeutronTestCase):
    def __init__(self, run_method='runTest'):
        super(TestExtraRoutes, self).__init__(run_method)
        self.net1 = None
        self.net2 = None
        self.subnet1 = None
        self.subnet2 = None
        self.router = None

    def setUp(self):
        self.net1 = self.create_network(name='net1')
        self.net2 = self.create_network(name='net2')
        self.subnet1 = self.create_subnet(
            name='subnet1', net_id=self.net1['id'], cidr='192.168.1.0/24')
        self.subnet2 = self.create_subnet(
            name='subnet2', net_id=self.net2['id'], cidr='192.168.2.0/24')
        self.router = self.create_router(
            name='router', pub_net_id=self.pub_network['id'],
            priv_sub_ids=[self.subnet1['id'], self.subnet2['id']])

    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    def test_extra_routes_1R2SN_multi_ip_interface_ping_same_hv(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'],
            hv_host=vm1.get_hypervisor_name())

        self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.16.0.2"}]}})

        # Add an extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')

        # Add extra route for router to route 172.16.0.2 to subnet1
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.2/32',
                    'nexthop': ip1
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.2'))

    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    @test_case.require_topology_feature('compute_hosts', operator.ge, 2)
    def test_extra_routes_1R2SN_multi_ip_interface_ping_diff_hv(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'],
            hv_host='!' + vm1.get_hypervisor_name())
        self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.16.0.2"}]}})

        # Add an extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')

        # Add extra route for router to route 172.16.0.2 to subnet1
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.2/32',
                    'nexthop': ip1
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.2'))

    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    @test_case.require_hosts(['ext1', 'router1', 'edge1'])
    def test_extra_routes_1R2SN_multi_ip_interface_ping_outside(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'],
            allowed_address_pairs=[('172.16.0.2',)])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'])

        self.create_edge_router()

        # Add an extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')

        # Add extra route for router to route 172.16.0.2 to subnet1
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.2/32',
                    'nexthop': ip1
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        ext_host = self.vtm.get_host('ext1')
        """
        :type: zephyr.underlay.underlay_host.UnderlayHost
        """
        ext_ip = ext_host.get_ip('eth0')
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    def test_extra_routes_1R2SN_multi_ip_interface_multiple_routes(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'])

        self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.16.0.2"},
                                          {"ip_address": "172.17.0.2"}]}})

        self.api.update_port(
            port2['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.18.0.2"}]}})

        # Add two extra IP addrs to vm1's interface and one to vm2
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')
        vm1.execute('ip a add 172.17.0.2/32 dev eth0')
        vm2.execute('ip a add 172.18.0.2/32 dev eth0')

        # Add extra route for router to route 172.16.0.2 to subnet1
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.2/32',
                    'nexthop': ip1
                },
                {
                    'destination': '172.17.0.2/32',
                    'nexthop': ip1
                },
                {
                    'destination': '172.18.0.2/32',
                    'nexthop': ip2
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.2'))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.17.0.2'))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.18.0.2'))

    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    def test_extra_routes_1R2SN_multi_ip_interface_ping_subnet_route(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'])

        self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.16.0.2"},
                                          {"ip_address": "172.16.0.3"}]}})

        # Add an extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')
        # Add another extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.3/32 dev eth0')

        # Add extra route for router to route 172.16.0.2 to subnet1
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.0/24',
                    'nexthop': ip1
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.2'))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.3'))

    @unittest.expectedFailure
    @require_extension("extraroute")
    @require_extension("allowed-address-pairs")
    def test_extra_routes_2R21N_add_extra_route(self):
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.net1['id'],
            gw_ip=self.subnet1['gateway_ip'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.net2['id'],
            gw_ip=self.subnet2['gateway_ip'])

        routerextra = self.create_router(name='routerextra')

        port1extra = self.create_port(
            name='port1extra', net_id=self.net1['id'])
        port2extra = self.create_port(
            name='port1extra', net_id=self.net2['id'])
        ip1extra = port1extra['fixed_ips'][0]['ip_address']
        ip2extra = port2extra['fixed_ips'][0]['ip_address']

        self.create_router_interface(
            router_id=routerextra['id'], port_id=port1extra['id'])
        self.create_router_interface(
            router_id=routerextra['id'], port_id=port2extra['id'])

        self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.16.0.2"}]}})

        self.api.update_port(
            port2['id'],
            {'port': {
                'allowed_address_pairs': [{"ip_address": "172.18.0.3"}]}})

        # Add an extra IP addr to vm1's interface
        vm1.execute('ip a add 172.16.0.2/32 dev eth0')
        # Add another extra IP addr to vm2's interface
        vm2.execute('ip a add 172.16.0.3/32 dev eth0')

        # Add extra route for router to route extra-IPs to use extra ports
        updatedef = {'router': {
            'routes': [
                {
                    'destination': '172.16.0.3/32',
                    'nexthop': ip1extra
                },
                {
                    'destination': '172.16.0.2/32',
                    'nexthop': ip2extra
                }
            ]
        }}
        self.api.update_router(self.router['id'], updatedef)

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.2'))

        self.LOG.info("Pinging from VM2 to VM1's extra address")
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, use_tcp=False, target_ip_addr='172.16.0.3'))
