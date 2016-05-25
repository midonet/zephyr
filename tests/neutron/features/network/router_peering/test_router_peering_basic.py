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

from router_peering_utils import L2GWNeutronTestCase


class TestRouterPeeringBasic(L2GWNeutronTestCase):

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_edge_and_vtep_router(self):
        try:
            self.connect_through_edge_and_vtep_router()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_vtep_router(self):
        try:
            self.connect_through_vtep_router()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    def connect_through_edge_and_vtep_router(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        a_pub_sub = self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
        a_tenant_router = self.create_router('EAST',
                                             pub_net_id=a_pub_net['id'],
                                             priv_sub_ids=[a_sub['id']])
        a_edge = self.create_edge_router(
            pub_subnets=[a_pub_sub],
            router_host_name='router1',
            edge_host_name='edge2',
            edge_iface_name='eth1',
            edge_subnet_cidr='172.17.2.0/24')
        (porta, vma, ipa) = self.create_vm_server(
            "A", a_net['id'], a_sub['gateway_ip'])
        a_fip = self.create_floating_ip(porta['id'], a_pub_net['id'])

        b_cidr = "192.168.30.0/24"
        b_pub_cidr = "200.200.130.0/24"
        b_net = self.create_network('WEST')
        b_sub = self.create_subnet('WEST', b_net['id'], b_cidr)
        b_pub_net = self.create_network('PUB_WEST', external=True)
        b_pub_sub = self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        b_edge = self.create_edge_router(
            pub_subnets=[b_pub_sub],
            router_host_name='router1',
            edge_host_name='edge1',
            edge_iface_name='eth1',
            edge_subnet_cidr='172.16.2.0/24')
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
        b_fip = self.create_floating_ip(portb['id'], b_pub_net['id'])

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
        a_rme = self.add_peer(
            a_peer_topo, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_peer_topo['az_iface_port']['id'], "2.2.2.2")
        a_router_mac = a_peer_topo['az_iface_port']['mac_address']
        b_rme = self.add_peer(
            b_peer_topo, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_peer_topo['az_iface_port']['id'], "1.1.1.2")

        exterior_ip = "172.20.1.1"
        vmb.start_echo_server(ip=ipb)

        import pdb; pdb.set_trace()

        self.verify_connectivity(vma, ipb)
        self.verify_connectivity(vma, b_fip['floating_ip_address'])

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)
        self.verify_connectivity(vmb, a_fip['floating_ip_address'])

        self.assertTrue(vma.ping(target_ip=exterior_ip))

    def connect_through_vtep_router(self):
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
        a_rme = self.add_peer(
            a_peer_topo, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_peer_topo['az_iface_port']['id'], "2.2.2.2")
        a_router_mac = a_peer_topo['az_iface_port']['mac_address']
        b_rme = self.add_peer(
            b_peer_topo, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_peer_topo['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)
