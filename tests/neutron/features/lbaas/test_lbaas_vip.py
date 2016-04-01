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


from tests.neutron.features.lbaas.lbaas_test_utils import DEFAULT_POOL_PORT
from tests.neutron.features.lbaas.lbaas_test_utils import LBaaSTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm.test_case import expected_failure

PACKETS_TO_SEND = 30


class TestLBaaSVIP(LBaaSTestCase):
    @require_extension('lbaas')
    def test_lbaas_vip_on_pool_subnet_pinger_on_pinger_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['lbaas']['subnet']['id']
            member_net = 'member'
            pinger_net = 'pinger'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_member_subnet_pinger_on_pinger_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['member']['subnet']['id']
            member_net = 'member'
            pinger_net = 'pinger'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_pinger_subnet_pinger_on_pinger_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['pinger']['subnet']['id']
            member_net = 'member'
            pinger_net = 'pinger'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_pinger_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.pub_subnet['id']
            member_net = 'member'
            pinger_net = 'pinger'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_pool_subnet_pinger_on_member_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['lbaas']['subnet']['id']
            member_net = 'member'
            pinger_net = 'member'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_member_subnet_pinger_on_member_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['member']['subnet']['id']
            member_net = 'member'
            pinger_net = 'member'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_isolated_subnet_pinger_on_member_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['pinger']['subnet']['id']
            member_net = 'member'
            pinger_net = 'member'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_member_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.pub_subnet['id']
            member_net = 'member'
            pinger_net = 'member'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_pool_subnet_pinger_on_pool_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['lbaas']['subnet']['id']
            member_net = 'member'
            pinger_net = 'lbaas'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_member_subnet_pinger_on_pool_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['member']['subnet']['id']
            member_net = 'member'
            pinger_net = 'lbaas'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_isolated_subnet_pinger_on_pool_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['pinger']['subnet']['id']
            member_net = 'member'
            pinger_net = 'lbaas'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_pool_subnet(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.pub_subnet['id']
            member_net = 'member'
            pinger_net = 'lbaas'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2,
                                         net=member_net)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

    @require_extension('lbaas')
    def test_lbaas_vip_add_member(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            pool_subnet = self.topos['main']['lbaas']['subnet']['id']
            vip_subnet = self.topos['main']['lbaas']['subnet']['id']
            member_net = 'member'
            pinger_net = 'pinger'

            poola = self.create_pool(subnet_id=pool_subnet)

            vipa = self.create_vip(subnet_id=vip_subnet,
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=3,
                                         net=member_net)

            g1 = vms[0]
            g2 = vms[1]
            g3 = vms[2]

            g_pinger = self.create_pinger_vm(net=pinger_net)

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

            self.create_member(pool_id=poola['id'],
                               ip=g3.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2, g3], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2, g3], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
