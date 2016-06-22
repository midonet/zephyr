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
import time
from zephyr.tsm.neutron_test_case import require_extension

PACKETS_TO_SEND = 40


class TestLBaaSUpdates(LBaaSTestCase):
    @require_extension('lbaas')
    def test_lbaas_delete_members(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            member1a = self.create_member(pool_id=poola['id'],
                                          ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND)

            self.delete_member(member1a['id'])

            repliesa = self.send_packets_to_vip(
                [g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g2], repliesa,
                total_expected=PACKETS_TO_SEND)

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_delete_readd_members(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            member1a = self.create_member(pool_id=poola['id'],
                                          ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND)

            self.delete_member(member1a['id'])

            repliesa = self.send_packets_to_vip(
                [g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g2], repliesa,
                total_expected=PACKETS_TO_SEND)

            self.assertFalse(g1.vm.vm_underlay.name in repliesa)

            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND)

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_update_pools_switch_subnet(self):
        try:
            self.create_member_net('main1')
            self.create_lbaas_net('main1')
            self.create_pinger_net('main1')
            self.create_lb_router('main1', gw_net_id=self.pub_network['id'])

            self.create_member_net('main2')
            self.create_lbaas_net('main2')
            self.create_pinger_net('main2')
            self.create_lb_router('main2', gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main1']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])

            vms = self.create_member_vms(name='main1',
                                         num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger1 = self.create_pinger_vm(name='main1')
            g_pinger2 = self.create_pinger_vm(name='main2')

            self.create_member(pool_id=poola['id'],
                               ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger1, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")

            self.api.update_pool(
                poola['id'],
                {'pool': {
                    'subnet_id': self.topos['main2']['lbaas']['subnet']['id']
                }})

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger2, vipa['address'],
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
    def test_lbaas_update_members_switch_pools(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])
            poolb = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vipb = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poolb-vip1',
                                   pool_id=poolb['id'])

            vms = self.create_member_vms(num_members=3)
            g1 = vms[0]
            g2 = vms[1]
            g3 = vms[2]

            g_pinger = self.create_pinger_vm()

            member1 = self.create_member(pool_id=poola['id'],
                                         ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)
            self.create_member(pool_id=poolb['id'],
                               ip_addr=g3.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)
            repliesb = self.send_packets_to_vip(
                [g3], g_pinger, vipb['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
            self.check_host_replies_against_rr_baseline(
                [g3], repliesb,
                total_expected=PACKETS_TO_SEND,
                identifier="poolB")

            member1 = self.api.update_member(
                member1['id'],
                {'member': {'pool_id': poolb['id']}})['member']

            self.LOG.debug('Updated member1 to LBaaS Pool B: ' + str(member1))

            repliesa = self.send_packets_to_vip(
                [g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)
            repliesb = self.send_packets_to_vip(
                [g1, g3], g_pinger, vipb['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
            self.check_host_replies_against_rr_baseline(
                [g1, g3], repliesb,
                total_expected=PACKETS_TO_SEND,
                identifier="poolB")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_update_hm_disassociate_kill_member_reassociate(self):
        try:

            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            hm = self.create_health_monitor()
            self.associate_health_monitor(hm_id=hm['id'],
                                          pool_id=poola['id'])
            time.sleep(10)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")

            self.api.disassociate_health_monitor(poola['id'], hm['id'])

            self.LOG.debug("Bringing down eth0 on VM: " +
                           str(g1.vm.vm_underlay.name))
            # Kill one member's TCP interface and make sure no more
            # packets get sent there
            g1.vm.vm_underlay.interface_down('eth0')

            time.sleep(10)

            replies = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            num_misses = replies['NO_RESPONSE']
            num_g1_hits = replies[g1.vm.vm_underlay.name]
            num_g2_hits = replies[g2.vm.vm_underlay.name]
            self.assertEqual(PACKETS_TO_SEND - num_g2_hits, num_misses)
            self.assertEqual(0, num_g1_hits)

            self.api.associate_health_monitor(
                poola['id'],
                {'health_monitor': {'tenant_id': 'admin',
                                    'id': hm['id']}})

            time.sleep(10)

            # g1 should now receive no packets, all should go to g2
            repliesa = self.send_packets_to_vip(
                [g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
