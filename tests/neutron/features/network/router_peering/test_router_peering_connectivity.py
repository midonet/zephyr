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

from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm.test_case import require_topology_feature
from zephyr.vtm.neutron_api import *

from router_peering_utils import L2GWNeutronTestCase


class TestRouterPeeringConnectivity(L2GWNeutronTestCase):

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_same_tenant(self):
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        try:

            east_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_east',
                    main_subnet_cidr=east_main_cidr,
                    pub_name='pub_east',
                    pub_subnet_cidr="200.200.120.0/24",
                    log=self.LOG)
            west_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_west',
                    main_subnet_cidr=west_main_cidr,
                    pub_name='pub_west',
                    pub_subnet_cidr="200.200.130.0/24",
                    log=self.LOG)

            port1 = self.api.create_port({
                'port': {'name': 'port_vm1',
                         'network_id': east_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1,
                    mac=port1['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port({
                'port': {'name': 'port_vm2',
                         'network_id': west_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm2 = self.vtm.create_vm(
                    ip=ip2,
                    mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            east_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                  "1.1.1.3", "tun2", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.2", segment_id,
                                                  east_topo.router.router,
                                                  "EAST")
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                  "2.2.2.3", "tun1", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.3", segment_id,
                                                  west_topo.router.router,
                                                  "WEST")
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # Test that VM1 can reach VM2 via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = vm2.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm2.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_external_connectivity(self):
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None
        east_ed = None
        west_ed = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        exterior_ip = "172.20.1.1"
        try:

            east_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_east',
                    main_subnet_cidr=east_main_cidr,
                    pub_name='pub_east',
                    pub_subnet_cidr="200.200.120.0/24",
                    log=self.LOG)
            west_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_west',
                    main_subnet_cidr=west_main_cidr,
                    pub_name='pub_west',
                    pub_subnet_cidr="200.200.130.0/24",
                    log=self.LOG)
            east_ed = self.create_edge_router(
                    pub_subnet=east_topo.pub_net.subnet,
                    router_host_name='router1',
                    edge_host_name='edge2',
                    edge_iface_name='eth1',
                    edge_subnet_cidr='172.17.2.0/24')
            west_ed = self.create_edge_router(
                    pub_subnet=west_topo.pub_net.subnet,
                    router_host_name='router1',
                    edge_host_name='edge1',
                    edge_iface_name='eth1',
                    edge_subnet_cidr='172.16.2.0/24')

            port1 = self.api.create_port(
                    {'port': {'name': 'port_vm1',
                              'network_id': east_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']

            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1,
                    mac=port1['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port(
                    {'port': {'name': 'port_vm2',
                              'network_id': west_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm2 = self.vtm.create_vm(
                    ip=ip2,
                    mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Peer the routers!
            east_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                  "1.1.1.3", "tun2", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.2", segment_id,
                                                  east_topo.router.router,
                                                  "EAST")
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                  "2.2.2.3", "tun1", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.3", segment_id,
                                                  west_topo.router.router,
                                                  "WEST")
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            self.assertTrue(vm1.ping(target_ip=exterior_ip))

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            if east_ed:
                self.delete_edge_router(east_ed)

            if west_ed:
                self.delete_edge_router(west_ed)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_floating_ip(self):
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None
        east_ed = None
        west_ed = None

        floating_ip_east = None
        floating_ip_west = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        try:

            east_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_east',
                    main_subnet_cidr=east_main_cidr,
                    pub_name='pub_east',
                    pub_subnet_cidr="200.200.120.0/24",
                    log=self.LOG)
            west_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_west',
                    main_subnet_cidr=west_main_cidr,
                    pub_name='pub_west',
                    pub_subnet_cidr="200.200.130.0/24",
                    log=self.LOG)
            east_ed = self.create_edge_router(
                    pub_subnet=east_topo.pub_net.subnet,
                    router_host_name='router1',
                    edge_host_name='edge2',
                    edge_iface_name='eth1',
                    edge_subnet_cidr='172.17.2.0/24')
            west_ed = self.create_edge_router(
                    pub_subnet=west_topo.pub_net.subnet,
                    router_host_name='router1',
                    edge_host_name='edge1',
                    edge_iface_name='eth1',
                    edge_subnet_cidr='172.16.2.0/24')

            port1 = self.api.create_port(
                    {'port': {'name': 'port_vm1',
                              'network_id': east_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1,
                    mac=port1['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port(
                    {'port': {'name': 'port_vm2',
                              'network_id': west_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm2 = self.vtm.create_vm(
                    ip=ip2,
                    mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Peer the routers!
            east_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                  "1.1.1.3", "tun2", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.2", segment_id,
                                                  east_topo.router.router,
                                                  "EAST")
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                  "2.2.2.3", "tun1", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.3", segment_id,
                                                  west_topo.router.router,
                                                  "WEST")
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            floating_ip_east = self.api.create_floatingip(
                    {'floatingip': {
                        'tenant_id': 'admin',
                        'port_id': port1['id'],
                        'floating_network_id':
                            east_topo.pub_net.network['id']}})['floatingip']

            floating_ip_west = self.api.create_floatingip(
                    {'floatingip': {
                        'tenant_id': 'admin',
                        'port_id': port2['id'],
                        'floating_network_id':
                            west_topo.pub_net.network['id']}})['floatingip']

            fip_e = floating_ip_east['floating_ip_address']
            self.LOG.debug("Received floating IP E: " + str(fip_e))
            fip_w = floating_ip_west['floating_ip_address']
            self.LOG.debug("Received floating IP W: " + str(fip_w))

            self.assertTrue(vm1.ping(target_ip=fip_w))
            self.assertTrue(vm2.ping(target_ip=fip_e))

            vm1.start_echo_server(ip=ip1, echo_data='pong_e')
            vm2.start_echo_server(ip=ip2, echo_data='pong_w')

            reply_e = vm1.send_echo_request(dest_ip=fip_w,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)
            reply_e = vm1.send_echo_request(dest_ip=ip2,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)

            reply_w = vm2.send_echo_request(dest_ip=fip_e,
                                            echo_request='ping_w')
            self.assertEqual('ping_w:pong_e', reply_w)
            reply_e = vm2.send_echo_request(dest_ip=ip2,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)

            reply_e = vm1.send_echo_request(dest_ip=fip_w,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)
            reply_e = vm1.send_echo_request(dest_ip=ip2,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)

            reply_w = vm2.send_echo_request(dest_ip=fip_e,
                                            echo_request='ping_w')
            self.assertEqual('ping_w:pong_e', reply_w)
            reply_e = vm2.send_echo_request(dest_ip=ip2,
                                            echo_request='ping_e')
            self.assertEqual('ping_e:pong_w', reply_e)

        finally:

            if floating_ip_east:
                self.api.update_floatingip(floating_ip_east['id'],
                                           {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip_east['id'])

            if floating_ip_west:
                self.api.update_floatingip(floating_ip_west['id'],
                                           {'floatingip': {'port_id': None}})
                self.api.delete_floatingip(floating_ip_west['id'])

            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            if east_ed:
                self.delete_edge_router(east_ed)

            if west_ed:
                self.delete_edge_router(west_ed)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_large_data(self):
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        try:

            east_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_east',
                    main_subnet_cidr=east_main_cidr,
                    pub_name='pub_east',
                    pub_subnet_cidr="200.200.120.0/24",
                    log=self.LOG)
            west_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_west',
                    main_subnet_cidr=west_main_cidr,
                    pub_name='pub_west',
                    pub_subnet_cidr="200.200.130.0/24",
                    log=self.LOG)

            port1 = self.api.create_port({
                'port': {'name': 'port_vm1',
                         'network_id': east_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1,
                    mac=port1['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port({
                'port': {'name': 'port_vm2',
                         'network_id': west_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm2 = self.vtm.create_vm(
                    ip=ip2,
                    mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            east_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                  "1.1.1.3", "tun2", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.2", segment_id,
                                                  east_topo.router.router,
                                                  "EAST")
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                  "2.2.2.3", "tun1", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.3", segment_id,
                                                  west_topo.router.router,
                                                  "WEST")
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # TCP with short data
            vm2.start_echo_server(ip=ip2, echo_data='pong')
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:pong', echo_response)

            # Send second packet
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:pong', echo_response)

            # TCP with exactly MTU-sized data
            # (MTU=1500 - (TCP + IP header size = 80)) - len(':pong')=5
            long_data = "O" * (1500 - 80 - 5)
            echo_response = vm1.send_echo_request(dest_ip=ip2,
                                                  echo_request=long_data)
            self.assertEqual(long_data + ':pong', echo_response)

            # Send second long packet
            echo_response = vm1.send_echo_request(dest_ip=ip2,
                                                  echo_request=long_data)
            self.assertEqual(long_data + ':pong', echo_response)

            # TCP with many times MTU-sized data
            long_data = "O" * 4500
            echo_response = vm1.send_echo_request(dest_ip=ip2,
                                                  echo_request=long_data)
            self.assertEqual(long_data + ':pong', echo_response)

            # Send second long packet
            echo_response = vm1.send_echo_request(dest_ip=ip2,
                                                  echo_request=long_data)
            self.assertEqual(long_data + ':pong', echo_response)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)
