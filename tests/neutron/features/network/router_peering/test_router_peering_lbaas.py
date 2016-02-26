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

from TSM.NeutronTestCase import GuestData
from TSM.NeutronTestCase import require_extension
from TSM.TestCase import require_topology_feature

from router_peering_utils import L2GWNeutronTestCase
from tests.neutron.features.lbaas.lbaas_test_utils import LBaaSTestCase
from tests.neutron.features.lbaas.lbaas_test_utils import DEFAULT_POOL_PORT

PACKETS_TO_SEND = 20
EGI = 'external_gateway_info'
EFI = 'external_fixed_ips'


class TestRouterPeeringLBaaS(L2GWNeutronTestCase, LBaaSTestCase):
    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_rotuers_with_lbaas_members_same_side_az(self):
        try:
            a_topo, b_topo = self.connect_through_vtep_router()

            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=a_topo['pub_network']['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=a_topo['pub_subnet']['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
        finally:
            self.clear_lbaas_data()
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_rotuers_with_lbaas_members_far_side_az(self):
        try:
            a_topo, b_topo = self.connect_through_vtep_router()

            poola = self.create_pool(
                subnet_id=a_topo['main_subnet']['id'])

            vipa = self.create_vip(subnet_id=a_topo['pub_subnet']['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])

            g1 = GuestData(*self.create_vm_server(
                name='m_mn_0',
                net_id=b_topo['main_network']['id'],
                gw_ip=b_topo['main_subnet']['gateway_ip']))
            g2 = GuestData(*self.create_vm_server(
                name='m_mn_1',
                net_id=b_topo['main_network']['id'],
                gw_ip=b_topo['main_subnet']['gateway_ip']))

            g_pinger = GuestData(*self.create_vm_server(
                name='p_mn',
                net_id=a_topo['main_network']['id'],
                gw_ip=a_topo['main_subnet']['gateway_ip']))

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_rotuers_with_lbaas_members_both_sides_az(self):
        try:
            a_topo, b_topo = self.connect_through_vtep_router()

            poola = self.create_pool(
                subnet_id=a_topo['main_subnet']['id'])

            vipa = self.create_vip(subnet_id=a_topo['pub_subnet']['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])

            g1 = GuestData(*self.create_vm_server(
                name='m_mn_0',
                net_id=a_topo['main_network']['id'],
                gw_ip=a_topo['main_subnet']['gateway_ip']))
            g2 = GuestData(*self.create_vm_server(
                name='m_mn_1',
                net_id=b_topo['main_network']['id'],
                gw_ip=b_topo['main_subnet']['gateway_ip']))

            g_pinger = GuestData(*self.create_vm_server(
                name='p_mn',
                net_id=a_topo['main_network']['id'],
                gw_ip=a_topo['main_subnet']['gateway_ip']))

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    def connect_through_vtep_router(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        a_pub_sub = self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
        a_tenant_router = self.create_router('EAST',
                                             pub_net_id=a_pub_net['id'],
                                             priv_sub_ids=[])
        a_tenant_router_port = self.create_port(
            name='main_tr_port',
            net_id=a_net['id'],
            sub_id=a_sub['id'],
            ip=a_sub['gateway_ip'])
        self.create_router_interface(
            router_id=a_tenant_router['id'],
            port_id=a_tenant_router_port['id'])

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
            tun_host="tun2",
            tun_iface="eth1",
            tenant_router_id=a_tenant_router['id'],
            segment_id="100")

        b_peer_topo = self.create_router_peering_topo(
            name="WEST",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.3",
            tun_cidr="2.2.2.0/24",
            tun_ip="2.2.2.2",
            tun_gw="2.2.2.3",
            tun_host="tun1",
            tun_iface="eth1",
            tenant_router_id=b_tenant_router['id'],
            segment_id="100")

        b_router_mac = b_peer_topo['az_iface_port']['mac_address']
        self.add_peer(
            a_peer_topo, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_peer_topo['az_iface_port']['id'], "2.2.2.2")
        a_router_mac = a_peer_topo['az_iface_port']['mac_address']
        self.add_peer(
            b_peer_topo, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_peer_topo['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)
        a_peer_topo['pub_network'] = a_pub_net
        a_peer_topo['pub_subnet'] = a_pub_sub
        a_peer_topo['main_network'] = a_net
        a_peer_topo['main_subnet'] = a_sub
        a_peer_topo['tenant_router'] = a_tenant_router
        b_peer_topo['pub_network'] = b_pub_net
        b_peer_topo['pub_subnet'] = b_pub_sub
        b_peer_topo['main_network'] = b_net
        b_peer_topo['main_subnet'] = b_sub
        b_peer_topo['tenant_router'] = b_tenant_router
        return a_peer_topo, b_peer_topo
