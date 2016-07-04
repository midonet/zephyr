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

from router_peering_utils import L2GWNeutronTestCase


class TestRouterPeeringComplexTopology(L2GWNeutronTestCase):

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @test_case.require_hosts(['tun1', 'tun2', 'tun3'])
    def test_peered_routers_multiple_peers(self):
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

        c_cidr = "192.168.40.0/24"
        c_pub_cidr = "200.200.140.0/24"
        c_net = self.create_network('NORTH')
        c_sub = self.create_subnet('NORTH', c_net['id'], c_cidr)
        c_pub_net = self.create_network('PUB_NORTH', external=True)
        c_pub_sub = self.create_subnet('PUB_NORTH', c_pub_net['id'],
                                       c_pub_cidr)
        c_tenant_router = self.create_router('NORTH',
                                             pub_net_id=c_pub_net['id'],
                                             priv_sub_ids=[c_sub['id']])
        (portc, vmc, ipc) = self.create_vm_server(
            "C", c_net['id'], c_sub['gateway_ip'])

        a_top = self.create_router_peering_topo(
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

        b_top = self.create_router_peering_topo(
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

        c_top = self.create_router_peering_topo(
            name="NORTH",
            az_cidr="192.168.200.0/24",
            az_gw="192.168.200.4",
            tun_cidr="3.3.3.0/24",
            tun_ip="3.3.3.2",
            tun_gw="3.3.3.3",
            tun_host="tun3",
            tun_iface="eth1",
            tenant_router_id=c_tenant_router['id'],
            segment_id="100")

        a_router_mac = a_top['az_iface_port']['mac_address']
        b_router_mac = b_top['az_iface_port']['mac_address']
        c_router_mac = c_top['az_iface_port']['mac_address']

        a_to_b_rme = self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        a_to_c_rme = self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.4", c_router_mac, c_cidr,
            c_top['az_iface_port']['id'], "3.3.3.2")

        b_to_a_rme = self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        self.api.update_router(
            a_tenant_router['id'],
            {'router': {'routes': [{'nexthop': "192.168.200.4",
                                    'destination': c_cidr},
                                   {'nexthop': "192.168.200.3",
                                    'destination': b_cidr}]}})

        vmb.start_echo_server(ip_addr=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip_addr=ipa)
        self.verify_connectivity(vmb, ipa)

        self.delete_remote_mac_entry(b_top['gateway_device']['id'],
                                     b_to_a_rme['remote_mac_entry']['id'])

        c_to_a_rme = self.add_peer(
            c_top, c_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmc.start_echo_server(ip_addr=ipc)
        self.verify_connectivity(vma, ipc)

        self.verify_connectivity(vmc, ipa)
