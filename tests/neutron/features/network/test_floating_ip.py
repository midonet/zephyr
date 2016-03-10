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
        # Allowed address pair must have IP address
        port1 = None
        vm1 = None
        ext_host = None
        ext_ip = None
        ip1 = None
        floating_ip1 = None
        ed = None
        try:
            ed = self.create_edge_router()

            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            floating_ip1 = self.api.create_floatingip(
                    {'floatingip': {'tenant_id': 'admin',
                                    'floating_network_id': self.pub_network['id']}})['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP: " + str(fip1))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            floating_ip1 = self.api.update_floatingip(floating_ip1['id'],
                                                      {'floatingip': {'port_id': port1['id']}})['floatingip']

            ext_host = self.ptm.impl_.hosts_by_name['ext1']
            """:type: Host"""
            ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

            # Test that VM can still contact exterior host
            # Ping
            self.assertTrue(vm1.ping(target_ip=ext_ip))

            # TCP
            ext_host.start_echo_server(ip=ext_ip)
            echo_response = vm1.send_echo_request(dest_ip=ext_ip)
            self.assertEqual('ping:echo-reply', echo_response)

            # TODO(micucci): Fix UDP
            # UDP
            # ext_host.stop_echo_server(ip=ext_ip)
            # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
            # echo_response = vm1.send_echo_request(dest_ip=ext_ip, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

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
            # echo_response = ext_host.send_echo_request(dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if ext_host and ext_ip:
                ext_host.stop_echo_server(ip=ext_ip)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            if floating_ip1:
                self.api.update_floatingip(floating_ip1['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            self.cleanup_vms([(vm1, port1)])
            self.delete_edge_router(ed)

    @require_extension('extraroute')
    def test_external_connectivity_via_fip_assigned_during_creation(self):
        # Allowed address pair must have IP address
        port1 = None
        vm1 = None
        ext_host = None
        ext_ip = None
        ip1 = None
        floating_ip1 = None
        ed = None
        try:
            ed = self.create_edge_router()
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {'tenant_id': 'admin',
                                'port_id': port1['id'],
                                'floating_network_id': self.pub_network['id']}})['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP: " + str(fip1))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            ext_host = self.ptm.impl_.hosts_by_name['ext1']
            """:type: Host"""
            ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

            # Test that VM can still contact exterior host
            # Ping
            self.assertTrue(vm1.ping(target_ip=ext_ip))

            # TCP
            ext_host.start_echo_server(ip=ext_ip)
            echo_response = vm1.send_echo_request(dest_ip=ext_ip)
            self.assertEqual('ping:echo-reply', echo_response)

            # TODO(micucci): Fix UDP
            # UDP
            # ext_host.stop_echo_server(ip=ext_ip)
            # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
            # echo_response = vm1.send_echo_request(dest_ip=ext_ip, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

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
            # echo_response = ext_host.send_echo_request(dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if ext_host and ext_ip:
                ext_host.stop_echo_server(ip=ext_ip)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            if floating_ip1:
                self.api.update_floatingip(floating_ip1['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            self.cleanup_vms([(vm1, port1)])

            self.delete_edge_router(ed)

    @expected_failure('MI-115')
    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_private_ip(self):
        # Allowed address pair must have IP address
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        floating_ip1 = None
        ed = None
        try:
            ed = self.create_edge_router()
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            floating_ip1 = self.api.create_floatingip(
                    {'floatingip': {'tenant_id': 'admin',
                                    'port_id': port1['id'],
                                    'floating_network_id': self.pub_network['id']}})['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

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
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            if floating_ip1:
                self.api.update_floatingip(floating_ip1['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.delete_edge_router(ed)

    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_one_site_source_has_fip(self):
        # Allowed address pair must have IP address
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        floating_ip1 = None
        floating_ip2 = None
        ed = None
        try:
            ed = self.create_edge_router()
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            floating_ip1 = self.api.create_floatingip(
                    {'floatingip': {'tenant_id': 'admin',
                                    'port_id': port1['id'],
                                    'floating_network_id': self.pub_network['id']}})['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            floating_ip2 = self.api.create_floatingip(
                    {'floatingip': {'tenant_id': 'admin',
                                    'port_id': port2['id'],
                                    'floating_network_id': self.pub_network['id']}})['floatingip']

            fip2 = floating_ip2['floating_ip_address']
            self.LOG.debug("Received floating IP2: " + str(fip2))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

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
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            if floating_ip1:
                self.api.update_floatingip(floating_ip1['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            if floating_ip2:
                self.api.update_floatingip(floating_ip2['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip2['id'])

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.delete_edge_router(ed)

    @require_extension('extraroute')
    def test_fip_to_fip_connectivity_two_sites(self):
        # Allowed address pair must have IP address
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        floating_ip1 = None
        floating_ip2 = None
        ed1 = None
        ed2 = None
        new_topo = None
        try:
            new_topo = create_neutron_main_pub_networks(self.api,
                                                        main_name='main_2', main_subnet_cidr='192.168.10.0/24',
                                                        pub_name='pub_2', pub_subnet_cidr='200.200.10.0/24',
                                                        log=self.LOG)
            ed1 = self.create_edge_router(pub_subnet=self.pub_subnet, router_host_name='router1',
                                          edge_host_name='edge1', edge_iface_name='eth1',
                                          edge_subnet_cidr='172.16.2.0/24')
            ed2 = self.create_edge_router(pub_subnet=new_topo.pub_net.subnet, router_host_name='router1',
                                          edge_host_name='edge2', edge_iface_name='eth1',
                                          edge_subnet_cidr='172.17.2.0/24')

            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': new_topo.main_net.network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            floating_ip1 = self.api.create_floatingip(
                {'floatingip': {'tenant_id': 'admin',
                                'port_id': port1['id'],
                                'floating_network_id': self.pub_network['id']}})['floatingip']

            fip1 = floating_ip1['floating_ip_address']
            self.LOG.debug("Received floating IP1: " + str(fip1))

            floating_ip2 = self.api.create_floatingip(
                {'floatingip': {'tenant_id': 'admin',
                                'port_id': port2['id'],
                                'floating_network_id': new_topo.pub_net.network['id']}})['floatingip']

            fip2 = floating_ip2['floating_ip_address']
            self.LOG.debug("Received floating IP2: " + str(fip2))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'],
                                     gw_ip=new_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

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
            # echo_response = vm1.send_echo_request(dest_ip=fip2, protocol='udp')
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
            # echo_response = vm2.send_echo_request(dest_ip=fip1, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            if floating_ip1:
                self.api.update_floatingip(floating_ip1['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip1['id'])

            if floating_ip2:
                self.api.update_floatingip(floating_ip2['id'], {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip2['id'])

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.delete_edge_router(ed1)
            self.delete_edge_router(ed2)
            delete_neutron_main_pub_networks(self.api, new_topo)
