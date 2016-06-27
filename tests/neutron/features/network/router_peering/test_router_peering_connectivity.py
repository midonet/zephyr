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
from zephyr.vtm import neutron_api

from router_peering_utils import L2GWNeutronTestCase


class TestRouterPeeringConnectivity(L2GWNeutronTestCase):
    def create_neutron_main_pub_networks(
            self, main_name, main_subnet_cidr, pub_name, pub_subnet_cidr):
        new_main_network = self.create_network(main_name)
        new_main_subnet = self.create_subnet(
            main_name + '_sub', net_id=new_main_network['id'],
            cidr=main_subnet_cidr)
        new_pub_network = self.create_network(pub_name, external=True)
        new_pub_subnet = self.create_subnet(
            pub_name + '_sub', net_id=new_pub_network['id'],
            cidr=pub_subnet_cidr)
        new_public_router = self.create_router(
            'main_pub_router', pub_net_id=new_pub_network['id'],
            priv_sub_ids=[new_main_subnet['id']])

        return neutron_api.BasicTopoData(
            neutron_api.NetData(new_main_network, new_main_subnet),
            neutron_api.NetData(new_pub_network, new_pub_subnet),
            neutron_api.RouterData(new_public_router, []))

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_large_data(self):
        vm1 = None
        vm2 = None
        ip2 = None
        port1 = None
        port2 = None

        east_l2gw_topo = None
        west_l2gw_topo = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        try:
            east_topo = self.create_neutron_main_pub_networks(
                main_name='main_east',
                main_subnet_cidr=east_main_cidr,
                pub_name='pub_east',
                pub_subnet_cidr="200.200.120.0/24")
            west_topo = self.create_neutron_main_pub_networks(
                main_name='main_west',
                main_subnet_cidr=west_main_cidr,
                pub_name='pub_west',
                pub_subnet_cidr="200.200.130.0/24")

            port1 = self.api.create_port({
                'port': {'name': 'port_vm1',
                         'network_id': east_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                ip=ip1, mac=port1['mac_address'],
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
                ip=ip2, mac=port2['mac_address'],
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
