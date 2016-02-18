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

from TSM.NeutronTestCase import require_extension
from TSM.TestCase import require_topology_feature
from VTM.NeutronAPI import *

from router_peering_utils import L2GWNeutronTestCase
from router_peering_utils import L2GWSiteData


class TestRouterPeeringComplexTopology(L2GWNeutronTestCase):

    servers = list()

    def create_server(self, net_id, gw_ip, name):
        port = self.api.create_port({'port': {'name': 'port_vm_' + name,
                                              'network_id': net_id,
                                              'admin_state_up': True,
                                              'tenant_id': 'admin'}})['port']
        ip = port['fixed_ips'][0]['ip_address']

        vm = self.vtm.create_vm(ip=ip, mac=port['mac_address'], gw_ip=gw_ip)

        vm.plugin_vm('eth0', port['id'])
        self.servers.append((port, ip, vm))
        return (port, ip, vm)

    def clean_servers(self):
        for (port, ip, vm) in self.servers:
            vm.stop_echo_server(ip=ip)
            self.cleanup_vms([(vm, port)])

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b, ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_multiple_azs(self):
        """
        Test 2 different AZ networks over 2 routers.
        """
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_l2conn_id = None
        west_l2conn_id = None

        east_left_topo = None
        east_right_topo = None
        east_left_l2gw_topo = None
        east_right_l2gw_topo = None
        west_left_topo = None
        west_right_topo = None
        west_left_l2gw_topo = None
        west_right_l2gw_topo = None
        west_vtep_router = None
        east_vtep_router = None

        peered_topo = None

        left_segment_id = '100'
        right_segment_id = '200'

        east_left_cidr = "192.168.20.0/24"
        west_left_cidr = "192.168.30.0/24"

        east_right_cidr = "192.168.40.0/24"
        west_right_cidr = "192.168.50.0/24"

        try:

            east_left_topo = create_neutron_main_pub_networks(
                self.api,
                main_name='east_left',
                main_subnet_cidr=east_left_cidr,
                pub_name='pub_east_left',
                pub_subnet_cidr="200.200.120.0/24",
                log=self.LOG)

            west_left_topo = create_neutron_main_pub_networks(
                self.api,
                main_name='west_left',
                main_subnet_cidr=west_left_cidr,
                pub_name='pub_west_left',
                pub_subnet_cidr="200.200.130.0/24",
                log=self.LOG)

            east_right_topo = create_neutron_main_pub_networks(
                self.api,
                main_name='east_right',
                main_subnet_cidr=east_right_cidr,
                pub_name='pub_east_right',
                pub_subnet_cidr="200.200.140.0/24",
                log=self.LOG)

            west_right_topo = create_neutron_main_pub_networks(
                self.api,
                main_name='west_right',
                main_subnet_cidr=west_right_cidr,
                pub_name='pub_west_right',
                pub_subnet_cidr="200.200.150.0/24",
                log=self.LOG)

            (port1, ip1, vm1) = self.create_server(
                east_left_topo.main_net.network['id'],
                east_left_topo.main_net.subnet['gateway_ip'],
                '1')
            (port2, ip2, vm2) = self.create_server(
                west_left_topo.main_net.network['id'],
                west_left_topo.main_net.subnet['gateway_ip'],
                '2')
            (port3, ip3, vm3) = self.create_server(
                east_right_topo.main_net.network['id'],
                east_right_topo.main_net.subnet['gateway_ip'],
                '3')
            (port4, ip4, vm4) = self.create_server(
                west_right_topo.main_net.network['id'],
                west_right_topo.main_net.subnet['gateway_ip'],
                '4')

            # Peer the routers!
            # EAST SIDE
            east_left_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                       "1.1.1.3", "tun2", "eth1",
                                                       "192.168.200.0/24",
                                                       "192.168.200.2", left_segment_id,
                                                       east_left_topo.router.router,
                                                       "EAST_LEFT")

            az_net_east_right = self.api.create_network(
                    {'network': {'name': 'az_net_EAST_RIGHT',
                                 'tenant_id': 'admin'}})['network']
            az_sub_east_right = self.api.create_subnet(
                    {'subnet': {'name': 'az_sub_EAST_RIGHT',
                                'tenant_id': 'admin',
                                'network_id': az_net_east_right['id'],
                                'enable_dhcp': False,
                                'gateway_ip': None,
                                'ip_version': 4,
                                'cidr': "192.168.201.0/24"}})['subnet']
            l2gw_id = east_left_l2gw_topo.l2dev.l2gw
            l2gw_conn = self.create_l2_gateway_connection(
                    az_net_east_right['id'], right_segment_id, l2gw_id)
            east_l2conn_id = l2gw_conn['id']

            east_peer_router_port = self.api.create_port(
                    {'port':
                     {'name': 'tenant_port_EAST_RIGHT',
                      'network_id': az_net_east_right['id'],
                      'admin_state_up': True,
                      'fixed_ips': [{'subnet_id': az_sub_east_right['id'],
                                     'ip_address': "192.168.201.2"}],
                      'tenant_id': 'admin'}})['port']
            east_peer_router_iface = self.api.add_interface_router(
                    east_right_topo.router.router['id'],
                    {'port_id': east_peer_router_port['id']})
            east_vtep_router = east_left_l2gw_topo.vtep_router.router
            self.api.update_router(
                    east_vtep_router['id'],
                    {'router': {
                        'routes': [{'nexthop': "1.1.1.3",
                                    'destination': '0.0.0.0/0'}]}})['router']

            # WEST SIDE
            west_left_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                       "2.2.2.3", "tun1", "eth1",
                                                       "192.168.200.0/24",
                                                       "192.168.200.3", left_segment_id,
                                                       west_left_topo.router.router,
                                                       "WEST_LEFT")

            az_net_west_right = self.api.create_network(
                    {'network': {'name': 'az_net_WEST_RIGHT',
                                 'tenant_id': 'admin'}})['network']
            az_sub_west_right = self.api.create_subnet(
                    {'subnet': {'name': 'az_sub_WEST_RIGHT',
                                'tenant_id': 'admin',
                                'network_id': az_net_west_right['id'],
                                'enable_dhcp': False,
                                'gateway_ip': None,
                                'ip_version': 4,
                                'cidr': "192.168.201.0/24"}})['subnet']
            l2gw_id = west_left_l2gw_topo.l2dev.l2gw
            l2gw_conn = self.create_l2_gateway_connection(az_net_west_right['id'],
                                                          right_segment_id, l2gw_id)
            west_l2conn_id = l2gw_conn['id']

            west_peer_router_port = self.api.create_port(
                    {'port':
                     {'name': 'tenant_port_WEST_RIGHT',
                      'network_id': az_net_west_right['id'],
                      'admin_state_up': True,
                      'fixed_ips': [{'subnet_id': az_sub_west_right['id'],
                                     'ip_address': "192.168.201.3"}],
                      'tenant_id': 'admin'}})['port']
            west_peer_router_iface = self.api.add_interface_router(
                    west_right_topo.router.router['id'],
                    {'port_id': west_peer_router_port['id']})
            west_vtep_router = west_left_l2gw_topo.vtep_router.router
            self.api.update_router(
                    west_vtep_router['id'],
                    {'router': {
                        'routes': [{'nexthop': "2.2.2.3",
                                    'destination': '0.0.0.0/0'}]}})['router']

            peered_topo = self.peer_sites(east=east_left_l2gw_topo,
                                          east_private_cidr=east_left_cidr,
                                          west=west_left_l2gw_topo,
                                          west_private_cidr=west_left_cidr,
                                          segment_id=left_segment_id)

            # Set up ghost port and remote mac entry on the east side
            self.api.update_router(
                east_right_topo.router.router['id'],
                {'router': {'routes': [{'nexthop': "192.168.201.3",
                                        'destination': west_right_cidr}]}})
            east_ghost_port = self.create_ghost_port(
                    az_net_east_right['id'], "192.168.201.3",
                    west_peer_router_port['mac_address'],
                    west_peer_router_port['id'])
            east_rmac = self.create_remote_mac_entry("2.2.2.2",
                    west_peer_router_port['mac_address'], right_segment_id,
                    east_left_l2gw_topo.l2dev.gwdev)

            # Set up ghost port and remote mac entry on the west side
            self.api.update_router(
                west_right_topo.router.router['id'],
                {'router': {'routes': [{'nexthop': "192.168.201.2",
                                        'destination': east_right_cidr}]}})
            west_ghost_port = self.create_ghost_port(
                    az_net_west_right['id'], "192.168.201.2",
                    east_peer_router_port['mac_address'],
                    east_peer_router_port['id'])
            west_rmac = self.create_remote_mac_entry("1.1.1.2",
                    east_peer_router_port['mac_address'], right_segment_id,
                    west_left_l2gw_topo.l2dev.gwdev)

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

            # Test that VM3 can reach VM4 via internal IP
            # Ping
            self.assertTrue(vm3.ping(target_ip=ip4))
            self.assertTrue(vm4.ping(target_ip=ip3))

            # TCP
            vm4.start_echo_server(ip=ip4)
            echo_response = vm3.send_echo_request(dest_ip=ip4)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm3.send_echo_request(dest_ip=ip4)
            self.assertEqual('ping:echo-reply', echo_response)

            # TCP
            vm3.start_echo_server(ip=ip3)
            echo_response = vm4.send_echo_request(dest_ip=ip3)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm4.send_echo_request(dest_ip=ip3)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            self.clean_servers()

            if east_ghost_port:
                self.api.delete_port(east_ghost_port['id'])
            if west_ghost_port:
                self.api.delete_port(west_ghost_port['id'])
            if east_l2conn_id:
                self.delete_l2_gw_conn(east_l2conn_id)
            if west_l2conn_id:
                self.delete_l2_gw_conn(west_l2conn_id)

            if west_peer_router_port:
                self.api.update_router(
                    west_right_topo.router.router['id'],
                    {'router': {'routes': None}})
                self.api.remove_interface_router(
                    west_right_topo.router.router['id'],
                    west_peer_router_iface)

            if east_peer_router_port:
                self.api.update_router(
                    east_right_topo.router.router['id'],
                    {'router': {'routes': None}})
                self.api.remove_interface_router(
                    east_right_topo.router.router['id'],
                    east_peer_router_iface)

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_left_l2gw_topo)
            self.clean_peer(west_left_l2gw_topo)
            self.clean_peer(east_right_l2gw_topo)
            self.clean_peer(west_right_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_left_topo)
            delete_neutron_main_pub_networks(self.api, west_left_topo)
            delete_neutron_main_pub_networks(self.api, east_right_topo)
            delete_neutron_main_pub_networks(self.api, west_right_topo)

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-3tun.json'])
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
        nort_main_cidr = "192.168.40.0/24"

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
            nort_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_nort',
                    main_subnet_cidr=nort_main_cidr,
                    pub_name='pub_nort',
                    pub_subnet_cidr="200.200.140.0/24",
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

            port3 = self.api.create_port({
                'port': {'name': 'port_vm3',
                         'network_id': nort_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip3 = port3['fixed_ips'][0]['ip_address']

            vm3 = self.vtm.create_vm(
                    ip=ip3,
                    mac=port3['mac_address'],
                    gw_ip=nort_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm3.plugin_vm('eth0', port3['id'])

            east_l2gw_topo = self.setup_peer_l2gw(
                "1.1.1.0/24", "1.1.1.2", "1.1.1.3", "tun2", "eth1",
                "192.168.200.0/24", "192.168.200.2", segment_id,
                east_topo.router.router, "EAST")
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw(
                "2.2.2.0/24", "2.2.2.2", "2.2.2.3", "tun1", "eth1",
                "192.168.200.0/24", "192.168.200.3", segment_id,
                west_topo.router.router, "WEST")
            nort_l2gw_topo = self.setup_peer_l2gw(
                "3.3.3.0/24", "3.3.3.2", "3.3.3.3", "tun3", "eth1",
                "192.168.200.0/24", "192.168.200.4", segment_id,
                nort_topo.router.router, "NORT")
            self.assertIsNotNone(nort_l2gw_topo)

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            az_net_east = east_l2gw_topo.az.network
            az_net_nort = nort_l2gw_topo.az.network
            nort_peer_router_port = nort_l2gw_topo.peer_router_port
            east_peer_router_port = east_l2gw_topo.peer_router_port

            self.api.update_router(
                east_topo.router.router['id'],
                {'router': {'routes': [{'nexthop': "192.168.200.4",
                                        'destination': nort_main_cidr},
                                       {'nexthop': "192.168.200.3",
                                        'destination': west_main_cidr}]}})
            east_ghost_port = self.create_ghost_port(
                    az_net_east['id'], "192.168.200.4",
                    nort_peer_router_port['mac_address'],
                    nort_peer_router_port['id'])
            east_rmac = self.create_remote_mac_entry("3.3.3.2",
                    nort_peer_router_port['mac_address'], segment_id,
                    east_l2gw_topo.l2dev.gwdev)

            self.api.update_router(
                nort_topo.router.router['id'],
                {'router': {'routes': [{'nexthop': "192.168.200.2",
                                        'destination': east_main_cidr}]}})
            nort_ghost_port = self.create_ghost_port(
                    az_net_nort['id'], "192.168.200.2",
                    east_peer_router_port['mac_address'],
                    east_peer_router_port['id'])
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

            self.delete_remote_mac_entry(
                peered_topo.east.gwdev_id, peered_topo.east.rmac_entry)

            nort_rmac = self.create_remote_mac_entry("1.1.1.2",
                    east_peer_router_port['mac_address'], segment_id,
                    nort_l2gw_topo.l2dev.gwdev)

            self.assertTrue(vm1.ping(target_ip=ip3))
            self.assertTrue(vm3.ping(target_ip=ip1))

            # TCP
            vm3.start_echo_server(ip=ip3)
            echo_response = vm1.send_echo_request(dest_ip=ip3)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm1.send_echo_request(dest_ip=ip3)
            self.assertEqual('ping:echo-reply', echo_response)

            # TCP
            echo_response = vm3.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm3.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            self.clean_topo()

            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            self.cleanup_vms([(vm1, port1), (vm2, port2), (vm3, port3)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)
            #TODO(joe): Fix cleanup
            #delete_neutron_main_pub_networks(self.api, nort_topo)
