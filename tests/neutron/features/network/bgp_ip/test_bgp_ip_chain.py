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

import time
from zephyr.tsm import neutron_test_case
from zephyr.tsm import test_case


class TestBGPIPChain(neutron_test_case.NeutronTestCase):

    @test_case.require_topology_feature('config_file', lambda a, b: a in b,
                                        ['2z-1c.json'])
    @neutron_test_case.require_extension('bgp-speaker-router-insertion')
    def test_bgp_ip_2_router(self):
        a_as = 64512
        b_as = 64513
        c_as = 64514

        a_cidr = "192.168.20.0/24"
        a_net = self.create_network('A_NET')
        a_sub = self.create_subnet('A_NET', a_net['id'], a_cidr)

        b_cidr = "192.168.30.0/24"
        b_net = self.create_network('B_NET')
        b_sub = self.create_subnet('B_NET', b_net['id'], b_cidr)

        c_cidr = "192.168.40.0/24"
        c_net = self.create_network('C_NET')
        self.create_subnet('C_NET', c_net['id'], c_cidr)

        a_router = self.create_router('A_ROUTER')
        aa_port = self.create_port('A_IFACE', a_net['id'],
                                   port_security_enabled=False)
        ac_port = self.create_port('AC_IFACE', c_net['id'],
                                   port_security_enabled=False)
        self.create_router_interface(a_router['id'], port_id=aa_port['id'])
        self.create_router_interface(a_router['id'], port_id=ac_port['id'])

        (porta, vma, ipa) = self.create_vm_server(
            "A", a_net['id'], a_sub['gateway_ip'])

        b_router = self.create_router('B_ROUTER')
        bb_port = self.create_port('B_IFACE', b_net['id'],
                                   port_security_enabled=False)
        bc_port = self.create_port('BC_IFACE', c_net['id'],
                                   port_security_enabled=False)
        self.create_router_interface(b_router['id'], port_id=bb_port['id'])
        self.create_router_interface(b_router['id'], port_id=bc_port['id'])

        a_bgp_speaker = self.create_bgp_speaker_curl('A_BGP', a_as,
                                                     a_router['id'])
        b_bgp_speaker = self.create_bgp_speaker_curl('B_BGP', b_as,
                                                     b_router['id'])

        a_peer_ip = bc_port['fixed_ips'][0]['ip_address']
        b_peer_ip = ac_port['fixed_ips'][0]['ip_address']

        a_peer = self.create_bgp_peer_curl('A_PEER', a_peer_ip, b_as)
        b_peer = self.create_bgp_peer_curl('B_PEER', b_peer_ip, a_as)

        self.add_bgp_speaker_peer(a_bgp_speaker['id'], a_peer['id'])
        self.add_bgp_speaker_peer(b_bgp_speaker['id'], b_peer['id'])

        vma.vm_underlay.reset_default_route(
            aa_port['fixed_ips'][0]['ip_address'])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])

        vmb.vm_underlay.reset_default_route(
            bb_port['fixed_ips'][0]['ip_address'])

        time.sleep(30)

        vmb.start_echo_server(ip_addr=ipb)
        self.check_ping_and_tcp(vma, ipb)

        vma.start_echo_server(ip_addr=ipa)
        self.check_ping_and_tcp(vmb, ipa)

        d_cidr = "192.168.50.0/24"
        d_net = self.create_network('D_NET')
        d_sub = self.create_subnet('D_NET', d_net['id'], d_cidr)

        c_router = self.create_router('C_ROUTER')

        cb_port = self.create_port('CB_IFACE', b_net['id'],
                                   port_security_enabled=False)
        self.create_router_interface(c_router['id'], port_id=cb_port['id'])

        cd_port = self.create_port('CD_IFACE', d_net['id'],
                                   port_security_enabled=False)
        self.create_router_interface(c_router['id'], port_id=cd_port['id'])

        c_bgp_speaker = self.create_bgp_speaker_curl('C_BGP', c_as,
                                                     c_router['id'])
        c_peer_ip = bb_port['fixed_ips'][0]['ip_address']
        c_peer = self.create_bgp_peer_curl('C_PEER', c_peer_ip, b_as)
        self.add_bgp_speaker_peer(c_bgp_speaker['id'], c_peer['id'])

        d_peer_ip = cb_port['fixed_ips'][0]['ip_address']
        d_peer = self.create_bgp_peer_curl('D_PEER', d_peer_ip, c_as)
        self.add_bgp_speaker_peer(b_bgp_speaker['id'], d_peer['id'])

        (portd, vmd, ipd) = self.create_vm_server(
            "LAST", d_net['id'], d_sub['gateway_ip'])
        vmd.vm_underlay.reset_default_route(
            cd_port['fixed_ips'][0]['ip_address'])

        time.sleep(30)
        vmd.start_echo_server(ip_addr=ipd)
        self.check_ping_and_tcp(vmd, ipa)
        self.check_ping_and_tcp(vma, ipd)
