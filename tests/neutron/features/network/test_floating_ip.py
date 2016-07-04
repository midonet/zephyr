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

import unittest

from zephyr.common import ip

from zephyr.tsm import neutron_test_case
from zephyr.tsm import test_case


class TestFloatingIP(neutron_test_case.NeutronTestCase):
    @neutron_test_case.require_extension('extraroute')
    def test_external_connectivity_via_fip_assigned_after_creation(self):
        # Create a SG to allow pings to come back into a FIP (just
        # for this one test to make sure forward flows from external hosts
        # can reach FIPs

        allowed_sg = self.create_security_group('allow_in')
        self.create_security_group_rule(
            sg_id=allowed_sg['id'],
            direction='ingress')
        self.create_edge_router()

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', self.main_network['id'],
            self.main_subnet['gateway_ip'],
            sgs=[allowed_sg['id']])
        floating_ip1 = self.create_floating_ip(
            pub_net_id=self.pub_network['id'])

        fip1 = floating_ip1['floating_ip_address']
        self.LOG.debug("Received floating IP: " + str(fip1))

        self.update_floating_ip(
            fip_id=floating_ip1['id'],
            port_id=port1['id'])

        ext_host = self.vtm.get_host('ext1')
        """
        :type: zephyr.underlay.underlay_host.UnderlayHost
        """
        ext_ip = ext_host.get_ip('eth0')
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        vm1.start_echo_server(ip_addr=ip1)

        # Test that VM can still contact exterior host
        self.assertTrue(vm1.verify_connection_to_host(ext_host))
        self.check_ping_and_tcp(ext_host, fip1)

    @neutron_test_case.require_extension('extraroute')
    def test_external_connectivity_via_fip_assigned_during_creation(self):
        self.create_edge_router()
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', self.main_network['id'],
            self.main_subnet['gateway_ip'])

        floating_ip1 = self.create_floating_ip(
            port_id=port1['id'],
            pub_net_id=self.pub_network['id'])

        fip1 = floating_ip1['floating_ip_address']
        self.LOG.debug("Received floating IP: " + str(fip1))

        ext_host = self.vtm.get_host('ext1')
        """
        :type: zephyr.underlay.underlay_host.UnderlayHost
        """
        ext_ip = ext_host.get_ip('eth0')
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        # Test that VM can still contact exterior host
        self.assertTrue(vm1.verify_connection_to_host(ext_host))

    @test_case.expected_failure('MI-115')
    @neutron_test_case.require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_private_ip(self):
        self.create_edge_router()
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', self.main_network['id'],
            self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', self.main_network['id'],
            self.main_subnet['gateway_ip'])

        floating_ip1 = self.create_floating_ip(
            pub_net_id=self.pub_network['id'],
            port_id=port1['id'])

        fip1 = floating_ip1['floating_ip_address']
        self.LOG.debug("Received floating IP1: " + str(fip1))

        # Test that VM can reach via internal IP
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.assertTrue(vm2.verify_connection_to_host(vm1))

        # Test that VM can reach via floating IP
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, target_ip_addr=fip1))

    @neutron_test_case.require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_fip(self):
        allowed_sg = self.create_security_group('allow_fip_in')
        self.create_security_group_rule(
            sg_id=allowed_sg['id'],
            remote_ip_prefix=self.pub_subnet['cidr'],
            direction='ingress')
        self.create_security_group_rule(
            sg_id=allowed_sg['id'],
            remote_group_id=allowed_sg['id'],
            direction='ingress')

        self.create_edge_router()
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', self.main_network['id'],
            self.main_subnet['gateway_ip'],
            sgs=[allowed_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', self.main_network['id'],
            self.main_subnet['gateway_ip'],
            sgs=[allowed_sg['id']])

        floating_ip1 = self.create_floating_ip(
            pub_net_id=self.pub_network['id'],
            port_id=port1['id'])
        floating_ip2 = self.create_floating_ip(
            pub_net_id=self.pub_network['id'],
            port_id=port2['id'])

        fip1 = floating_ip1['floating_ip_address']
        self.LOG.debug("Received floating IP1: " + str(fip1))
        fip2 = floating_ip2['floating_ip_address']
        self.LOG.debug("Received floating IP2: " + str(fip2))

        # Test that VM can reach via internal IP
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.assertTrue(vm2.verify_connection_to_host(vm1))

        # Test that VM can reach via floating IP
        self.assertTrue(vm1.verify_connection_to_host(
            vm2, target_ip_addr=fip2))
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, target_ip_addr=fip1))

    @neutron_test_case.require_extension('extraroute')
    @unittest.skip("The deletion of the exter subnet keeps screwing up")
    def test_fip_to_fip_connectivity_two_sites(self):
        new_main_network = self.create_network('main')
        new_main_subnet = self.create_subnet(
            'main_sub', net_id=new_main_network['id'],
            cidr='192.168.10.0/24')
        new_pub_network = self.create_network('public', external=True)
        new_pub_subnet = self.create_subnet(
            'public_sub', net_id=new_pub_network['id'],
            cidr='200.200.10.0/24')
        self.create_router(
            'main_pub_router', pub_net_id=new_pub_network['id'],
            priv_sub_ids=[new_main_subnet['id']])

        self.create_edge_router(
            pub_subnets=[self.pub_subnet], router_host_name='router1',
            edge_host_name='edge1', edge_iface_name='eth1',
            edge_subnet_cidr='172.16.2.0/24')
        self.create_edge_router(
            pub_subnets=[new_pub_subnet],
            router_host_name='router1',
            edge_host_name='edge2', edge_iface_name='eth1',
            edge_subnet_cidr='172.17.2.0/24')

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', self.main_network['id'],
            self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', new_main_network['id'],
            new_main_subnet['gateway_ip'])

        floating_ip1 = self.create_floating_ip(
            port_id=port1['id'],
            pub_net_id=self.pub_network['id'])

        fip1 = floating_ip1['floating_ip_address']
        self.LOG.debug("Received floating IP1: " + str(fip1))

        floating_ip2 = self.create_floating_ip(
            port_id=port2['id'],
            pub_net_id=new_pub_network['id'])

        fip2 = floating_ip2['floating_ip_address']
        self.LOG.debug("Received floating IP2: " + str(fip2))

        # Test that VM canNOT reach via internal IP
        self.assertFalse(vm1.ping(target_ip=ip2))
        self.assertFalse(vm2.ping(target_ip=ip1))

        # Test that VM1 can reach VM2 via FIP
        self.assertTrue(vm1.verify_connection_to_host(
            vm2, target_ip_addr=fip2))
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, target_ip_addr=fip1))

        # Test that VM2 can reach VM1 via FIP
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, target_ip_addr=fip1))

    @neutron_test_case.require_extension('extraroute')
    @test_case.expected_failure('MI-953')
    def test_fips_with_multiple_subnets_on_single_public_network(self):
        # New public top with a 30-bit mask (so 200.200.10.0-3 are
        # valid addresses, with 0=net addr, 1=gw addr, and 3=bcast addr)
        new_pub = self.create_network(
            name="pub_2_net",
            external=True)
        new_pub_sub1 = self.create_subnet(
            name="pub_2_sub1",
            net_id=new_pub['id'],
            cidr="200.200.10.0/30",
            enable_dhcp=False)
        new_pub_sub2 = self.create_subnet(
            name="pub_2_sub2",
            net_id=new_pub['id'],
            cidr="200.200.10.4/30",
            enable_dhcp=False)
        new_main = self.create_network(
            name="main_2_net")
        new_main_sub = self.create_subnet(
            name="main_2_sub",
            net_id=new_main['id'],
            cidr='192.168.10.0/24')

        self.create_router(
            name="main2_pub2_router",
            pub_net_id=new_pub['id'],
            priv_sub_ids=[new_main_sub['id']])

        self.create_edge_router(
            pub_subnets=[new_pub_sub1, new_pub_sub2],
            router_host_name='router1',
            edge_host_name='edge1', edge_iface_name='eth1',
            edge_subnet_cidr='172.16.2.0/24')

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', new_main['id'],
            new_main_sub['gateway_ip'])

        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', new_main['id'],
            new_main_sub['gateway_ip'])

        # Allocate the only FIP for the first CIDR
        fip_a = self.create_floating_ip(
            port_id=port1['id'],
            pub_net_id=new_pub['id'])
        self.assertEqual('200.200.10.2', fip_a['floating_ip_address'])

        # This SHOULD allocate the only FIP for the second CIDR
        self.create_floating_ip(
            port_id=port2['id'],
            pub_net_id=new_pub['id'])
        self.assertEqual('200.200.10.6', fip_a['floating_ip_address'])

        ext_host = self.vtm.get_host('ext1')
        """
        :type: zephyr.underlay.underlay_host.UnderlayHost
        """
        ext_ip = ext_host.get_ip('eth0')
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        # Test that each VM can still contact exterior host and each other
        # Ping
        self.assertTrue(vm1.verify_connection_to_host(
            ext_host, target_ip_addr=ext_ip))
        self.assertTrue(vm2.verify_connection_to_host(
            ext_host, target_ip_addr=ext_ip))
        self.assertTrue(vm1.verify_connection_to_host(
            vm2, target_ip_addr=ip2))
        self.assertTrue(vm2.verify_connection_to_host(
            vm1, target_ip_addr=ip1))
