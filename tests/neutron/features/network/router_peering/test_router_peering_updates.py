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

import json

from common.Utils import curl_post, curl_delete
from TSM.NeutronTestCase import require_extension
from TSM.TestCase import require_topology_feature
from VTM.Guest import Guest
from VTM.NeutronAPI import *

from router_peering_utils import \
    L2GWNeutronTestCase, L2GWSiteData, L2GWDevice, \
    L2GWSiteTopo, L2GWPeeredTopo, L2GWPeer


class TestRouterPeeringUpdates(L2GWNeutronTestCase):

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file',
                              lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_router_restart(self):
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
        east_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="1.1.1.0/24",
                tunnel_ip="1.1.1.2",
                tunnel_gw="1.1.1.3",
                tunnel_uplink_host="tun2",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.2")

        west_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="2.2.2.0/24",
                tunnel_ip="2.2.2.2",
                tunnel_gw="2.2.2.3",
                tunnel_uplink_host="tun1",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.3")

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

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # Peer the routers!
            east_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=east_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=east_topo.router.router,
                    peer_name='East')
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=west_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=west_topo.router.router,
                    peer_name='West')
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(
                    east=east_l2gw_topo,
                    east_private_cidr=east_main_cidr,
                    west=west_l2gw_topo,
                    west_private_cidr=west_main_cidr,
                    segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            self.api.update_router(
                    east_l2gw_topo.peer_router.router['id'],
                    {'router': {'routes': None}})

            # Remove the peer router's interface to the AZ net
            if east_l2gw_topo.peer_router and \
                    east_l2gw_topo.peer_router.router:
                if east_l2gw_topo.peer_router.if_list:
                    for i in east_l2gw_topo.peer_router.if_list:
                        self.api.remove_interface_router(
                                east_l2gw_topo.peer_router.router['id'], i)

            # remove ghost port and remote mac on west side
            self.clean_peered_site_data(peered_topo.west)

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('', echo_response)

            peer_router_port = self.api.create_port(
                    {'port': {'name': 'tenant_port_East',
                              'network_id': east_l2gw_topo.az.network['id'],
                              'admin_state_up': True,
                              'fixed_ips': [{
                                  'subnet_id': east_l2gw_topo.az.subnet['id'],
                                  'ip_address': east_side_l2gw_data.az_gw}],
                              'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created replacement port for peer router '
                           'on AZ East network: ' +
                           str(peer_router_port))

            # Re-add the peer router's interface to the AZ net
            new_if = self.api.add_interface_router(
                    east_l2gw_topo.peer_router.router['id'],
                    {'port_id': peer_router_port['id']})

            east_l2gw_topo = L2GWSiteTopo(
                    tunnel=east_l2gw_topo.tunnel,
                    tunnel_ip=east_l2gw_topo.tunnel_ip,
                    vtep_router=east_l2gw_topo.vtep_router,
                    l2dev=east_l2gw_topo.l2dev,
                    az=east_l2gw_topo.az,
                    peer_router=RouterData(
                            router=east_l2gw_topo.peer_router.router,
                            if_list=[new_if]),
                    peer_router_port=peer_router_port)

            west_port = west_l2gw_topo.peer_router_port
            west_port_ip_list = west_port['fixed_ips']
            west_port_main_ip_struct = west_port_ip_list[0]
            west_port_main_ip = west_port_main_ip_struct['ip_address']
            self.api.update_router(
                east_l2gw_topo.peer_router.router['id'],
                {'router': {'routes': [{'nexthop': west_port_main_ip,
                                        'destination': west_main_cidr}]}})

            east_port_ip_list = peer_router_port['fixed_ips']
            east_port_main_ip_struct = east_port_ip_list[0]
            east_port_main_ip = east_port_main_ip_struct['ip_address']
            # Recreate the ghost port and remote mac entry
            fake_peer_port_west = self.api.create_port(
                    {'port': {
                        'tenant_id': 'admin',
                        'fixed_ips': [{
                            'ip_address': east_port_main_ip
                        }],
                        'name': 'ghost_port_for_east_router',
                        'mac_address': peer_router_port['mac_address'],
                        'network_id': west_l2gw_topo.az.network['id'],
                        'port_security_enabled': False,
                        'device_owner': 'network:remote_site',
                        'device_id': peer_router_port['id']}})['port']
            self.LOG.debug("Recreated ghost port on west network mimicking "
                           "east-side router port: " +
                           str(fake_peer_port_west))

            mac_add_data_west = \
                {"remote_mac_entry": {
                    "tenant_id": "admin",
                    "vtep_address":
                        east_l2gw_topo.tunnel_ip,
                    "mac_address":
                        peer_router_port['mac_address'],
                    "segmentation_id": segment_id}}

            rmac_json_ret = \
                curl_post(
                        get_neutron_api_url(self.api) +
                        '/gw/gateway_devices/' +
                        str(west_l2gw_topo.l2dev.gwdev) +
                        "/remote_mac_entries",
                        json_data=mac_add_data_west)
            self.LOG.debug("RMAC West: " + str(rmac_json_ret))
            rmac_json = json.loads(rmac_json_ret)
            rmac_entry_west = rmac_json['remote_mac_entry']['id']

            peered_topo = L2GWPeeredTopo(peered_topo.east,
                                         L2GWPeer(rmac_entry_west,
                                                  west_l2gw_topo.l2dev.gwdev,
                                                  fake_peer_port_west))

            # Test that VM can once again reach via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            echo_response = vm1.send_echo_request(dest_ip=ip2)
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
    def test_peered_routers_add_reboot_vms(self):
        vm1 = None
        vm2 = None
        vm3 = None
        vm4 = None
        ip2 = None
        ip3 = None
        port1 = None
        port2 = None
        port3 = None
        port4 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None

        peered_topo = None
        east_side_l2gw_data = L2GWSiteData(tunnel_cidr="1.1.1.0/24",
                                           tunnel_ip="1.1.1.2",
                                           tunnel_gw="1.1.1.3",
                                           tunnel_uplink_host="tun2",
                                           tunnel_uplink_iface="eth1",
                                           az_cidr="192.168.200.0/24",
                                           az_gw="192.168.200.2")

        west_side_l2gw_data = L2GWSiteData(tunnel_cidr="2.2.2.0/24",
                                           tunnel_ip="2.2.2.2",
                                           tunnel_gw="2.2.2.3",
                                           tunnel_uplink_host="tun1",
                                           tunnel_uplink_iface="eth1",
                                           az_cidr="192.168.200.0/24",
                                           az_gw="192.168.200.3")

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

            port1 = self.api.create_port(
                    {'port': {'name': 'port_vm1',
                              'network_id': east_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1, mac=port1['mac_address'],
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
                    ip=ip2, mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # Peer the routers!
            east_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=east_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=east_topo.router.router,
                    peer_name='East')
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=west_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=west_topo.router.router,
                    peer_name='West')
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(
                    east=east_l2gw_topo,
                    east_private_cidr=east_main_cidr,
                    west=west_l2gw_topo,
                    west_private_cidr=west_main_cidr,
                    segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)
            vm2.stop_echo_server(ip=ip2)

            port3 = self.api.create_port(
                    {'port': {'name': 'port_vm1',
                              'network_id': east_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip3 = port3['fixed_ips'][0]['ip_address']

            vm3 = self.vtm.create_vm(
                    ip=ip3,
                    mac=port3['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm3.plugin_vm('eth0', port3['id'])

            port4 = self.api.create_port(
                    {'port': {'name': 'port_vm1',
                              'network_id': west_topo.main_net.network['id'],
                              'admin_state_up': True,
                              'tenant_id': 'admin'}})['port']
            ip4 = port4['fixed_ips'][0]['ip_address']

            vm4 = self.vtm.create_vm(
                    ip=ip4,
                    mac=port4['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm4.plugin_vm('eth0', port4['id'])

            # TCP
            vm3.start_echo_server(ip=ip3)
            echo_response = vm4.send_echo_request(dest_ip=ip3)
            self.assertEqual('ping:echo-reply', echo_response)

            vm2.vm_host.reboot()

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)
            echo_response = vm3.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm3 and ip3:
                vm3.stop_echo_server(ip=ip3)

            self.cleanup_vms([(vm1, port1), (vm2, port2),
                              (vm3, port3), (vm4, port4)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file',
                              lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_remove_readd_l2gw(self):
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
        east_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="1.1.1.0/24",
                tunnel_ip="1.1.1.2",
                tunnel_gw="1.1.1.3",
                tunnel_uplink_host="tun2",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.2")

        west_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="2.2.2.0/24",
                tunnel_ip="2.2.2.2",
                tunnel_gw="2.2.2.3",
                tunnel_uplink_host="tun1",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.3")

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
            east_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=east_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=east_topo.router.router,
                    peer_name='East')
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=west_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=west_topo.router.router,
                    peer_name='West')
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(
                    east=east_l2gw_topo,
                    east_private_cidr=east_main_cidr,
                    west=west_l2gw_topo,
                    west_private_cidr=west_main_cidr,
                    segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # Remove the L2GW Conn and device
            self.LOG.debug("Cleaning L2GW Conn:" +
                           get_neutron_api_url(self.api) +
                           "/l2-gateway-connections/" +
                           str(west_l2gw_topo.l2dev.l2conn))
            curl_delete(get_neutron_api_url(self.api) +
                        "/l2-gateway-connections/" +
                        str(west_l2gw_topo.l2dev.l2conn))

            self.LOG.debug("Cleaning L2GW:" +
                           get_neutron_api_url(self.api) +
                           "/l2-gateways/" +
                           str(west_l2gw_topo.l2dev.l2gw))
            curl_delete(get_neutron_api_url(self.api) +
                        "/l2-gateways/" +
                        str(west_l2gw_topo.l2dev.l2gw))

            # Make sure the connection is indeed broken
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # TCP
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('', echo_response)

            # Re-add the L2GW
            l2gw_curl = {
                "l2_gateway": {
                    "name": 'vtep_router_gw_West',
                    "devices": [{"device_id": west_l2gw_topo.l2dev.gwdev}],
                    "tenant_id": "admin"}}

            # Set up L2GW
            l2_json_ret = curl_post(get_neutron_api_url(self.api) +
                                    '/l2-gateways',
                                    l2gw_curl)
            self.LOG.debug('L2GW West: ' + str(l2_json_ret))
            l2_json = json.loads(l2_json_ret)
            l2gw_id = l2_json['l2_gateway']['id']

            # Re-add the l2gw connection
            l2gwc_curl = {
                "l2_gateway_connection": {
                    "network_id": west_l2gw_topo.az.network['id'],
                    "segmentation_id": segment_id,
                    "l2_gateway_id": l2gw_id,
                    "tenant_id": "admin"}}

            l2_conn_json_ret = curl_post(get_neutron_api_url(self.api) +
                                         '/l2-gateway-connections',
                                         l2gwc_curl)
            self.LOG.debug('L2 Conn West: ' + str(l2_conn_json_ret))
            l2_conn_json = json.loads(l2_conn_json_ret)
            l2conn_id = l2_conn_json['l2_gateway_connection']['id']

            west_l2gw_topo = L2GWSiteTopo(
                    tunnel=west_l2gw_topo.tunnel,
                    tunnel_ip=west_l2gw_topo.tunnel_ip,
                    vtep_router=west_l2gw_topo.vtep_router,
                    l2dev=L2GWDevice(gwdev=west_l2gw_topo.l2dev.gwdev,
                                     l2gw=l2gw_id,
                                     l2conn=l2conn_id),
                    az=west_l2gw_topo.az,
                    peer_router=west_l2gw_topo.peer_router,
                    peer_router_port=west_l2gw_topo.peer_router_port)

            # Test that VM can once again reach via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            echo_response = vm1.send_echo_request(dest_ip=ip2)
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
    @require_topology_feature('config_file',
                              lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_routers_remove_readd_l2gwconn(self):
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
        east_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="1.1.1.0/24",
                tunnel_ip="1.1.1.2",
                tunnel_gw="1.1.1.3",
                tunnel_uplink_host="tun2",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.2")

        west_side_l2gw_data = L2GWSiteData(
                tunnel_cidr="2.2.2.0/24",
                tunnel_ip="2.2.2.2",
                tunnel_gw="2.2.2.3",
                tunnel_uplink_host="tun1",
                tunnel_uplink_iface="eth1",
                az_cidr="192.168.200.0/24",
                az_gw="192.168.200.3")

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
            east_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=east_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=east_topo.router.router,
                    peer_name='East')
            self.assertIsNotNone(east_l2gw_topo)
            west_l2gw_topo = self.setup_peer_l2gw(
                    l2gw_site_data=west_side_l2gw_data,
                    segment_id=segment_id,
                    peer_router=west_topo.router.router,
                    peer_name='West')
            self.assertIsNotNone(west_l2gw_topo)

            peered_topo = self.peer_sites(
                    east=east_l2gw_topo,
                    east_private_cidr=east_main_cidr,
                    west=west_l2gw_topo,
                    west_private_cidr=west_main_cidr,
                    segment_id=segment_id)
            self.assertIsNotNone(peered_topo)

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # Remove the L2GW Conn only
            self.LOG.debug("Cleaning L2GW Conn:" +
                           get_neutron_api_url(self.api) +
                           "/l2-gateway-connections/" +
                           str(west_l2gw_topo.l2dev.l2conn))
            curl_delete(get_neutron_api_url(self.api) +
                        "/l2-gateway-connections/" +
                        str(west_l2gw_topo.l2dev.l2conn))

            # Make sure the connection is indeed broken
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # TCP
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('', echo_response)

            # Re-add the l2gw connection
            l2gwc_curl = {
                "l2_gateway_connection": {
                    "network_id": west_l2gw_topo.az.network['id'],
                    "segmentation_id": segment_id,
                    "l2_gateway_id": west_l2gw_topo.l2dev.l2gw,
                    "tenant_id": "admin"}}

            l2_conn_json_ret = curl_post(get_neutron_api_url(self.api) +
                                         '/l2-gateway-connections',
                                         l2gwc_curl)
            self.LOG.debug('L2 Conn West: ' + str(l2_conn_json_ret))
            l2_conn_json = json.loads(l2_conn_json_ret)
            l2conn_id = l2_conn_json['l2_gateway_connection']['id']

            west_l2gw_topo = L2GWSiteTopo(
                    tunnel=west_l2gw_topo.tunnel,
                    tunnel_ip=west_l2gw_topo.tunnel_ip,
                    vtep_router=west_l2gw_topo.vtep_router,
                    l2dev=L2GWDevice(gwdev=west_l2gw_topo.l2dev.gwdev,
                                     l2gw=west_l2gw_topo.l2dev.l2gw,
                                     l2conn=l2conn_id),
                    az=west_l2gw_topo.az,
                    peer_router=west_l2gw_topo.peer_router,
                    peer_router_port=west_l2gw_topo.peer_router_port)

            # Test that VM can once again reach via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            echo_response = vm1.send_echo_request(dest_ip=ip2)
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
