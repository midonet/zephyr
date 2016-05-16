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

from zephyr.tsm.test_case import expected_failure
from zephyr.vtm.neutron_api import create_neutron_main_pub_networks
from zephyr.vtm.neutron_api import delete_neutron_main_pub_networks

from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension


class TestFloatingIP(NeutronTestCase):
    @require_extension('extraroute')
    def test_external_connectivity_via_fip_assigned_after_creation(self):
        floating_ip1 = None
        try:
            self.create_edge_router()

            (port1, vm1, ip1) = self.create_vm_server(
                'vm1', self.main_network['id'],
                self.main_subnet['gateway_ip'])

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP: " + str(fip1))

            floating_ip1 = self.api.update_floatingip(
                floating_ip1['id'],
                {'floatingip': {'port_id': port1['id']}})['floatingip']

            ext_host = self.ptm.impl_.hosts_by_name['ext1']
            """:type: Host"""
            ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

            # Test that VM can still contact exterior host
            # Ping
            self.assertTrue(vm1.ping(target_ip=ext_ip))

            try:
                # TCP
                ext_host.start_echo_server(ip=ext_ip)
                echo_response = vm1.send_echo_request(dest_ip=ext_ip)
                self.assertEqual('ping:echo-reply', echo_response)

                # TODO(micucci): Fix UDP
                # UDP
                # ext_host.stop_echo_server(ip=ext_ip)
                # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
                # echo_response = vm1.send_echo_request(
                #   dest_ip=ext_ip, protocol='udp')
                # self.assertEqual('ping:echo-reply', echo_response)

            finally:
                ext_host.stop_echo_server(ip=ext_ip)

            # Now test exterior host can contact VM via FIP
            # Ping
            self.assertTrue(ext_host.ping(target_ip=fip1))

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = ext_host.send_echo_request(dest_ip=fip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # UDP
            # vm1.stop_echo_server(ip=ext_ip)
            # vm1.start_echo_server(ip=ip1, protocol='udp')
            # echo_response = ext_host.send_echo_request(
            #   dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)
        finally:
            if floating_ip1:
                self.api.update_floatingip(
                    floating_ip1['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

    @require_extension('extraroute')
    def test_external_connectivity_via_fip_assigned_during_creation(self):
        floating_ip1 = None
        try:
            self.create_edge_router()
            (port1, vm1, ip1) = self.create_vm_server(
                'vm1', self.main_network['id'],
                self.main_subnet['gateway_ip'])

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port1['id'],
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP: " + str(fip1))

            ext_host = self.ptm.impl_.hosts_by_name['ext1']
            """:type: Host"""
            ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

            # Test that VM can still contact exterior host
            # Ping
            self.assertTrue(vm1.ping(target_ip=ext_ip))

            try:
                # TCP
                ext_host.start_echo_server(ip=ext_ip)
                echo_response = vm1.send_echo_request(dest_ip=ext_ip)
                self.assertEqual('ping:echo-reply', echo_response)

                # TODO(micucci): Fix UDP
                # UDP
                # ext_host.stop_echo_server(ip=ext_ip)
                # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
                # echo_response = vm1.send_echo_request(
                #   dest_ip=ext_ip, protocol='udp')
                # self.assertEqual('ping:echo-reply', echo_response)

            finally:
                ext_host.stop_echo_server(ip=ext_ip)

            # Now test exterior host can contact VM via FIP
            # Ping
            self.assertTrue(ext_host.ping(target_ip=fip1))

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = ext_host.send_echo_request(dest_ip=fip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # UDP
            # vm1.stop_echo_server(ip=ext_ip)
            # vm1.start_echo_server(ip=ip1, protocol='udp')
            # echo_response = ext_host.send_echo_request(
            #   dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if floating_ip1:
                self.api.update_floatingip(
                    floating_ip1['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

    @expected_failure('MI-115')
    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_private_ip(self):
        floating_ip1 = None
        try:
            self.create_edge_router()
            (port1, vm1, ip1) = self.create_vm_server(
                'vm1', self.main_network['id'],
                self.main_subnet['gateway_ip'])
            (port2, vm2, ip2) = self.create_vm_server(
                'vm2', self.main_network['id'],
                self.main_subnet['gateway_ip'])

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port1['id'],
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            # Test that VM can reach via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            # Test that VM2 can reach VM1 via FIP
            # Ping
            self.assertTrue(vm2.ping(target_ip=fip1))

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = vm2.send_echo_request(dest_ip=fip1)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if floating_ip1:
                self.api.update_floatingip(
                    floating_ip1['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_fip(self):
        floating_ip1 = None
        floating_ip2 = None
        try:
            self.create_edge_router()
            (port1, vm1, ip1) = self.create_vm_server(
                'vm1', self.main_network['id'],
                self.main_subnet['gateway_ip'])
            (port2, vm2, ip2) = self.create_vm_server(
                'vm2', self.main_network['id'],
                self.main_subnet['gateway_ip'])

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port1['id'],
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            floating_ip2 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port2['id'],
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip2 = floating_ip2['floating_ip_address']
            self.LOG.debug("Received floating IP2: " + str(fip2))

            # Test that VM can reach via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            # Test that VM1 can reach VM2 via FIP
            # Ping
            self.assertTrue(vm1.ping(target_ip=fip2))

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=fip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # Test that VM2 can reach VM1 via FIP
            # Ping
            self.assertTrue(vm2.ping(target_ip=fip1))

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = vm2.send_echo_request(dest_ip=fip1)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if floating_ip1:
                self.api.update_floatingip(
                    floating_ip1['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            if floating_ip2:
                self.api.update_floatingip(
                    floating_ip2['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip2['id'])

    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_two_sites(self):
        floating_ip1 = None
        floating_ip2 = None
        new_topo = None
        try:
            new_topo = create_neutron_main_pub_networks(
                self.api,
                main_name='main_2', main_subnet_cidr='192.168.10.0/24',
                pub_name='pub_2', pub_subnet_cidr='200.200.10.0/24',
                log=self.LOG)
            self.create_edge_router(
                pub_subnets=self.pub_subnet, router_host_name='router1',
                edge_host_name='edge1', edge_iface_name='eth1',
                edge_subnet_cidr='172.16.2.0/24')
            self.create_edge_router(
                pub_subnets=new_topo.pub_net.subnet,
                router_host_name='router1',
                edge_host_name='edge2', edge_iface_name='eth1',
                edge_subnet_cidr='172.17.2.0/24')

            (port1, vm1, ip1) = self.create_vm_server(
                'vm1', self.main_network['id'],
                self.main_subnet['gateway_ip'])
            (port2, vm2, ip2) = self.create_vm_server(
                'vm2', new_topo.main_net.network['id'],
                new_topo.main_net.subnet['gateway_ip'])

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port1['id'],
                    'floating_network_id': self.pub_network['id']}}
            )['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            floating_ip2 = self.api.create_floatingip(
                {'floatingip': {
                    'tenant_id': 'admin',
                    'port_id': port2['id'],
                    'floating_network_id': new_topo.pub_net.network['id']}}
            )['floatingip']

            fip2 = floating_ip2['floating_ip_address']
            self.LOG.debug("Received floating IP2: " + str(fip2))

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # Test that VM1 can reach VM2 via FIP
            # Ping
            self.assertTrue(vm1.ping(target_ip=fip2))
            self.assertTrue(vm2.ping(target_ip=fip1))

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=fip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # TODO(micucci): Fix UDP
            # UDP
            # ext_host.stop_echo_server(ip=ip2)
            # ext_host.start_echo_server(ip=ip2, protocol='udp')
            # echo_response = vm1.send_echo_request(
            #   dest_ip=fip2, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

            # Test that VM2 can reach VM1 via FIP
            # Ping
            self.assertTrue(vm2.ping(target_ip=fip1))

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = vm2.send_echo_request(dest_ip=fip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # UDP
            # vm1.stop_echo_server(ip=ip1)
            # vm1.start_echo_server(ip=ip1, protocol='udp')
            # echo_response = vm2.send_echo_request(
            #   dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if floating_ip1:
                self.api.update_floatingip(
                    floating_ip1['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            if floating_ip2:
                self.api.update_floatingip(
                    floating_ip2['id'],
                    {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip2['id'])

            delete_neutron_main_pub_networks(self.api, new_topo)

    @require_extension('extraroute')
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
        fip_b = self.create_floating_ip(
            port_id=port2['id'],
            pub_net_id=new_pub['id'])
        self.assertEqual('200.200.10.6', fip_a['floating_ip_address'])

        ext_host = self.ptm.impl_.hosts_by_name['ext1']
        """:type: Host"""
        ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

        # Test that each VM can still contact exterior host and each other
        # Ping
        self.assertTrue(vm1.ping(target_ip=ext_ip))
        self.assertTrue(vm2.ping(target_ip=ext_ip))
        self.assertTrue(vm1.ping(target_ip=ip2))
        self.assertTrue(vm2.ping(target_ip=ip1))

        try:
            # TCP
            ext_host.start_echo_server(ip=ext_ip)
            echo_response = vm1.send_echo_request(dest_ip=ext_ip)
            self.assertEqual('ping:echo-reply', echo_response)

            echo_response2 = vm2.send_echo_request(dest_ip=ext_ip)
            self.assertEqual('ping:echo-reply', echo_response2)

        finally:
            ext_host.stop_echo_server(ip=ext_ip)
