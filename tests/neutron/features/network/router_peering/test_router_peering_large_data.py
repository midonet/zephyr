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
from zephyr.tsm import test_case
from zephyr.vtm import neutron_api

from router_peering_utils import L2GWNeutronTestCase


class TestRouterPeeringLargeData(L2GWNeutronTestCase):
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
    @test_case.require_hosts(['tun1', 'tun2'])
    def test_peered_routers_large_data(self):
        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

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

        (port1, vm1, ip1) = self.create_vm_server(
            name='vm1',
            net_id=east_topo.main_net.network['id'],
            gw_ip=east_topo.main_net.subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            name='vm2',
            net_id=west_topo.main_net.network['id'],
            gw_ip=west_topo.main_net.subnet['gateway_ip'])

        east_l2gw_topo = self.create_router_peering_topo(
            name="EAST",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.2",
            tun_cidr="1.1.1.0/24",
            tun_ip="1.1.1.2",
            tun_gw="1.1.1.3",
            tun_host="tun2",
            tun_iface="eth1",
            tenant_router_id=east_topo.router.router['id'],
            segment_id="100")
        self.assertIsNotNone(east_l2gw_topo)

        west_l2gw_topo = self.create_router_peering_topo(
            name="WEST",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.3",
            tun_cidr="2.2.2.0/24",
            tun_ip="2.2.2.2",
            tun_gw="2.2.2.3",
            tun_host="tun1",
            tun_iface="eth1",
            tenant_router_id=west_topo.router.router['id'],
            segment_id="100")
        self.assertIsNotNone(west_l2gw_topo)

        e_router_mac = east_l2gw_topo['az_iface_port']['mac_address']
        w_router_mac = west_l2gw_topo['az_iface_port']['mac_address']
        e_rme = self.add_peer(
            east_l2gw_topo, east_topo.router.router['id'], "100",
            "192.168.200.3", w_router_mac, west_main_cidr,
            west_l2gw_topo['az_iface_port']['id'], "2.2.2.2")
        w_rme = self.add_peer(
            west_l2gw_topo, west_topo.router.router['id'], "100",
            "192.168.200.2", e_router_mac, east_main_cidr,
            east_l2gw_topo['az_iface_port']['id'], "1.1.1.2")

        self.assertIsNotNone(e_rme)
        self.assertIsNotNone(w_rme)

        vm2.start_echo_server(ip_addr=ip2)

        # TCP with short data
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
