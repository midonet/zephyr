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

import time

from zephyr.tsm import neutron_test_case
from zephyr.tsm import test_case


class TestBGPIPExtraRoutes(neutron_test_case.NeutronTestCase):

    @test_case.require_topology_feature('config_file', lambda a, b: a in b,
                                        ['2z-1c.json'])
    @neutron_test_case.require_extension('bgp-speaker-router-insertion')
    def test_bgp_ip_2_router(self):
        a_as = 64512
        b_as = 64513

        a_cidr = "192.168.20.0/24"
        a_net = self.create_network('A_NET')
        a_sub = self.create_subnet('A_NET', a_net['id'], a_cidr)

        a2_cidr = "192.168.50.0/24"
        a2_net = self.create_network('A2_NET')
        a2_sub = self.create_subnet('A2_NET', a2_net['id'], a2_cidr)

        b_cidr = "192.168.30.0/24"
        b_net = self.create_network('B_NET')
        b_sub = self.create_subnet('B_NET', b_net['id'], b_cidr)

        c_cidr = "192.168.100.0/24"
        c_net = self.create_network('C_NET')
        c_sub = self.create_subnet('C_NET', c_net['id'], c_cidr)

        a_router = self.create_router('A_ROUTER')
        aa_port = self.create_port('A_IFACE', a_net['id'],
                                   port_security_enabled=False)
        ac_port = self.create_port('AC_IFACE', c_net['id'],
                                   port_security_enabled=False)

        self.create_router_interface(a_router['id'], port_id=aa_port['id'])
        self.create_router_interface(a_router['id'], port_id=ac_port['id'])

        a_bgp_speaker = self.create_bgp_speaker_curl(
            'A_BGP', a_as, a_router['id'])

        b_router = self.create_router('B_ROUTER')
        bb_port = self.create_port('B_IFACE', b_net['id'],
                                   port_security_enabled=False)
        bc_port = self.create_port('BC_IFACE', c_net['id'],
                                   port_security_enabled=False)
        self.create_router_interface(b_router['id'], port_id=bb_port['id'])
        self.create_router_interface(b_router['id'], port_id=bc_port['id'])

        b_bgp_speaker = self.create_bgp_speaker_curl(
            'B_BGP', b_as, b_router['id'])

        a2_router = self.create_router('A2_ROUTER')
        a2a2_port = self.create_port('A2A2_IFACE', a2_net['id'],
                                     port_security_enabled=False)

        a2a_port = self.create_port('A2A_IFACE', a_net['id'],
                                    port_security_enabled=False)
        self.create_router_interface(a2_router['id'], port_id=a2a_port['id'])
        self.create_router_interface(a2_router['id'], port_id=a2a2_port['id'])

        aa_peer_ip = aa_port['fixed_ips'][0]['ip_address']
        a2a_peer_ip = a2a_port['fixed_ips'][0]['ip_address']

        # Routes from A2 router to the B network
        self.add_routes(a2_router['id'], [(b_cidr, aa_peer_ip)])
        # Routes from A router to the A2 network (should be learned by B!)
        self.add_routes(a_router['id'], [(a2_cidr, a2a_peer_ip)])

        (porta, vma, ipa) = self.create_vm_server(
            "A", a2_net['id'], a2_sub['gateway_ip'])

        a_peer_ip = bc_port['fixed_ips'][0]['ip_address']
        b_peer_ip = ac_port['fixed_ips'][0]['ip_address']

        a_peer = self.create_bgp_peer_curl(
            'A_PEER', a_peer_ip, b_as)
        b_peer = self.create_bgp_peer_curl(
            'B_PEER', b_peer_ip, a_as)

        self.add_bgp_speaker_peer(a_bgp_speaker['id'], a_peer['id'])
        self.add_bgp_speaker_peer(b_bgp_speaker['id'], b_peer['id'])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", b_net['id'], b_sub['gateway_ip'])

        vma.vm_host.reset_default_route(
            a2a2_port['fixed_ips'][0]['ip_address'])
        vmb.vm_host.reset_default_route(bb_port['fixed_ips'][0]['ip_address'])

        time.sleep(60)

        vmb.start_echo_server(ip=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip=ipa)
        self.verify_connectivity(vmb, ipa)
