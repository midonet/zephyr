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

from router_peering_utils import L2GWNeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension


class TestRouterPeeringUpdates(L2GWNeutronTestCase):

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_router_restart(self):
        try:
            self.router_restart()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_add_reboot_vms(self):
        try:
            self.add_reboot_vms()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_remove_readd_l2gw(self):
        try:
            self.remove_readd_l2gw()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_remove_readd_l2gwconn(self):
        try:
            self.remove_readd_l2gwconn()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_peered_routers_update_tunnel_ip(self):
        try:
            self.update_tunnel_ip()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    def router_restart(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
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
        self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
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

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        a_rme = self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        b_rme = self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        self.api.update_router(a_tenant_router['id'],
                               {'router': {'routes': None}})
        self.remove_router_interface(a_tenant_router['id'],
                                     a_top['az_iface'])

        self.delete_port(a_rme['ghost_port']['id'])
        self.delete_port(b_rme['ghost_port']['id'])

        self.delete_remote_mac_entry(a_top['gateway_device']['id'],
                                     a_rme['remote_mac_entry']['id'])
        self.delete_remote_mac_entry(b_top['gateway_device']['id'],
                                     b_rme['remote_mac_entry']['id'])

        self.assertFalse(vma.ping(target_ip=ipb))
        self.assertFalse(vmb.ping(target_ip=ipa))

        (iface_port, iface) = self.hook_tenant_router_to_az_net(
            "EAST", a_tenant_router['id'], a_top['az_net']['id'],
            a_top['az_sub']['id'], "192.168.200.2")
        a_top['az_iface_port'] = iface_port
        a_top['az_iface'] = iface

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        self.verify_connectivity(vma, ipb)
        self.verify_connectivity(vmb, ipa)

    def add_reboot_vms(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
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
        self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
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

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        a_rme = self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        b_rme = self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        self.api.update_router(a_tenant_router['id'],
                               {'router': {'routes': None}})
        self.remove_router_interface(a_tenant_router['id'],
                                     a_top['az_iface'])

        self.delete_port(a_rme['ghost_port']['id'])
        self.delete_port(b_rme['ghost_port']['id'])

        self.delete_remote_mac_entry(a_top['gateway_device']['id'],
                                     a_rme['remote_mac_entry']['id'])
        self.delete_remote_mac_entry(b_top['gateway_device']['id'],
                                     b_rme['remote_mac_entry']['id'])

        self.assertFalse(vma.ping(target_ip=ipb))
        self.assertFalse(vmb.ping(target_ip=ipa))

        (iface_port, iface) = self.hook_tenant_router_to_az_net(
            "EAST", a_tenant_router['id'], a_top['az_net']['id'],
            a_top['az_sub']['id'], "192.168.200.2")
        a_top['az_iface_port'] = iface_port
        a_top['az_iface'] = iface

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        vma.stop_echo_server(ip=ipa)
        vmb.stop_echo_server(ip=ipb)

        (portc, vmc, ipc) = self.create_vm_server(
            "C", a_net['id'], a_sub['gateway_ip'])
        (portd, vmd, ipd) = self.create_vm_server(
            "D", b_net['id'], b_sub['gateway_ip'])

        vmc.start_echo_server(ip=ipc)
        self.verify_connectivity(vmd, ipc)

        vmb.vm_underlay.reboot()

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

    def remove_readd_l2gw(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
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
        self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
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

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        self.delete_l2_gw_conn(a_top['l2_gateway_conn']['id'])
        self.delete_l2_gateway(a_top['l2_gateway']['id'])

        self.assertFalse(vma.ping(target_ip=ipb))
        self.assertFalse(vmb.ping(target_ip=ipa))

        l2gw = self.create_l2_gateway("EAST", a_top['gateway_device']['id'])
        self.create_l2_gateway_connection(a_top['az_net']['id'], "100",
                                          l2gw['id'])

        self.verify_connectivity(vma, ipb)
        self.verify_connectivity(vmb, ipa)

    def remove_readd_l2gwconn(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
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
        self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
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

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        self.delete_l2_gw_conn(a_top['l2_gateway_conn']['id'])

        self.assertFalse(vma.ping(target_ip=ipb))
        self.assertFalse(vmb.ping(target_ip=ipa))

        self.create_l2_gateway_connection(a_top['az_net']['id'], "100",
                                          a_top['l2_gateway']['id'])

        self.verify_connectivity(vma, ipb)
        self.verify_connectivity(vmb, ipa)

    def update_tunnel_ip(self):
        a_cidr = "192.168.20.0/24"
        a_pub_cidr = "200.200.120.0/24"
        a_net = self.create_network('EAST')
        a_sub = self.create_subnet('EAST', a_net['id'], a_cidr)
        a_pub_net = self.create_network('PUB_EAST', external=True)
        self.create_subnet('PUB_EAST', a_pub_net['id'], a_pub_cidr)
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
        self.create_subnet('PUB_WEST', b_pub_net['id'], b_pub_cidr)
        b_tenant_router = self.create_router('WEST',
                                             pub_net_id=b_pub_net['id'],
                                             priv_sub_ids=[b_sub['id']])
        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])
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

        b_router_mac = b_top['az_iface_port']['mac_address']
        a_router_mac = a_top['az_iface_port']['mac_address']

        a_rme = self.add_peer(
            a_top, a_tenant_router['id'], "100",
            "192.168.200.3", b_router_mac, b_cidr,
            b_top['az_iface_port']['id'], "2.2.2.2")

        self.add_peer(
            b_top, b_tenant_router['id'], "100",
            "192.168.200.2", a_router_mac, a_cidr,
            a_top['az_iface_port']['id'], "1.1.1.2")

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)

        new_tunnel_ip = '2.2.2.6'

        self.update_gw_device(b_top['gateway_device']['id'],
                              new_tunnel_ip)

        self.api.update_router(b_top['vtep_router']['id'],
                               {'router': {'routes': None}})
        self.remove_router_interface(b_top['vtep_router']['id'],
                                     b_top['vtep_tun_if'])

        tun_port = self.create_uplink_port(
            "WEST", b_top['vtep_net']['id'], "tun1", "eth1",
            b_top['vtep_sub']['id'], new_tunnel_ip)

        self.create_router_interface(
            b_top['vtep_router']['id'], tun_port['id'])

        route = {u'destination': u'0.0.0.0/0', u'nexthop': u'2.2.2.3'}
        self.api.update_router(b_top['vtep_router']['id'],
                               {'router': {'routes': [route]}})

        self.delete_remote_mac_entry(a_top['gateway_device']['id'],
                                     a_rme['remote_mac_entry']['id'])

        self.create_remote_mac_entry(new_tunnel_ip,
                                     b_top['az_iface_port']['mac_address'],
                                     "100", a_top['gateway_device']['id'])

        self.verify_connectivity(vma, ipb)
        self.verify_connectivity(vmb, ipa)
