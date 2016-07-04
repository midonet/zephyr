# Copyright 2016 Midokura SARL
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

from router_peering_utils import L2GWNeutronTestCase
import time
from zephyr.tsm import neutron_test_case
from zephyr.tsm import test_case


class TestRouterPeeringBGP(L2GWNeutronTestCase):

    @neutron_test_case.require_extension('extraroute')
    @neutron_test_case.require_extension('gateway-device')
    @neutron_test_case.require_extension('l2-gateway')
    @test_case.require_topology_feature('config_file', lambda a, b: a in b,
                                        ['2z-1c-root-2tun.json'])
    @unittest.skip("TODO: Topology loading does not work.")
    def test_bgp_ip_router_peering(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        a_pub_sub = self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
        a_tenant_router = self.create_router('EAST',
                                             pub_net_id=a_pub_net['id'],
                                             priv_sub_ids=[a_sub['id']])
        (porta, vma, ipa) = self.create_vm_server(
            "A", a_net['id'], a_sub['gateway_ip'])

        b_cidr = "192.168.30.0/24"
        b_pub_cidr = "200.200.130.0/24"
        b_net = self.create_network('WEST')
        b_sub = self.create_subnet('WEST', b_net['id'], b_cidr)
        b_pub_net = self.create_network('PUB_WEST', external=True)
        b_pub_sub = self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
        a_peer_topo = self.create_router_peering_topo(
            name="EAST",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.2",
            tun_cidr="1.1.1.0/24",
            tun_ip="1.1.1.2",
            tun_gw="1.1.1.3",
            tun_host="cmp1",
            tun_iface="eth5",
            tenant_router_id=a_tenant_router['id'],
            segment_id="100")

        b_peer_topo = self.create_router_peering_topo(
            name="WEST",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.3",
            tun_cidr="2.2.2.0/24",
            tun_ip="2.2.2.2",
            tun_gw="2.2.2.3",
            tun_host="cmp1",
            tun_iface="eth6",
            tenant_router_id=b_tenant_router['id'],
            segment_id="100")

        b_router_mac = b_peer_topo['az_iface_port']['mac_address']
        a_rme = self.add_peer(
            a_peer_topo, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_peer_topo['az_iface_port']['id'], "2.2.2.2", add_route=False)
        a_router_mac = a_peer_topo['az_iface_port']['mac_address']
        b_rme = self.add_peer(
            b_peer_topo, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_peer_topo['az_iface_port']['id'], "1.1.1.2", add_route=False)

        a_as = 64512
        b_as = 64513

        a_bgp_speaker = self.create_bgp_speaker_curl(
            'A_BGP', a_as, a_tenant_router['id'])
        b_bgp_speaker = self.create_bgp_speaker_curl(
            'B_BGP', b_as, b_tenant_router['id'])

        a_peer = self.create_bgp_peer_curl('A_PEER', '192.168.200.3', b_as)
        b_peer = self.create_bgp_peer_curl('B_PEER', '192.168.200.2', a_as)

        self.add_bgp_speaker_peer(a_bgp_speaker['id'], a_peer['id'])
        self.add_bgp_speaker_peer(b_bgp_speaker['id'], b_peer['id'])

        # bgpd takes about a minute to peer up and learn routes
        time.sleep(60)

        vmb.start_echo_server(ip_addr=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip_addr=ipa)
        self.verify_connectivity(vmb, ipa)
