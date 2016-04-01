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

from tests.neutron.features.lbaas.lbaas_test_utils import *
from zephyr.tsm.neutron_test_case import require_extension

PACKETS_TO_SEND = 40


class TestLBaaSMultiplePools(LBaaSTestCase):
    """
    Test LBaaS multiple pools.  All tests have pinger VM on its
    own subnet and the VIP on the public subnet.
    """
    @require_extension('lbaas')
    def test_lbaas_multiple_pools_same_subnet(self):
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
                                   protocol_port=DEFAULT_POOL_PORT + 1,
                                   name='poolb-vip1',
                                   pool_id=poolb['id'])
            vms = self.create_member_vms(num_members=4)
            g1a = vms[0]
            g1b = vms[1]
            g2a = vms[2]
            g2b = vms[3]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip=g1a.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g1b.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g2a.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g2b.ip)

            repliesa = self.send_packets_to_vip(
                [g1a, g2a], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)
            repliesb = self.send_packets_to_vip(
                [g1b, g2b], g_pinger, vipb['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1a, g2a], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
            self.check_host_replies_against_rr_baseline(
                [g1b, g2b], repliesb,
                total_expected=PACKETS_TO_SEND,
                identifier="poolB")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_multiple_pools_multiple_subnets(self):
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
            poolb = self.create_pool(
                subnet_id=self.topos['main2']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vipb = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT + 1,
                                   name='poolb-vip1',
                                   pool_id=poolb['id'])

            vms1 = self.create_member_vms(name='main1',
                                          num_members=2)
            vms2 = self.create_member_vms(name='main2',
                                          num_members=2)
            g1a = vms1[0]
            g1b = vms1[1]
            g2a = vms2[0]
            g2b = vms2[1]

            g_pinger1 = self.create_pinger_vm(name='main1')
            g_pinger2 = self.create_pinger_vm(name='main2')

            self.create_member(pool_id=poola['id'],
                               ip=g1a.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g1b.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g2a.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g2b.ip)

            repliesa = self.send_packets_to_vip(
                [g1a, g1a], g_pinger1, vipa['address'],
                num_packets=PACKETS_TO_SEND)
            repliesb = self.send_packets_to_vip(
                [g1b, g2b], g_pinger2, vipb['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1a, g2a], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
            self.check_host_replies_against_rr_baseline(
                [g1b, g2b], repliesb,
                total_expected=PACKETS_TO_SEND,
                identifier="poolB")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_multiple_pools_shared_members(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])
            poolb = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])
            poolc = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vipb = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT + 1,
                                   name='poolb-vip1',
                                   pool_id=poolb['id'])
            vipc = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT + 1,
                                   name='poolc-vip1',
                                   pool_id=poolc['id'])

            vms1 = self.create_member_vms(name='main',
                                          num_members=4)
            g1 = vms1[0]
            g2 = vms1[1]
            g3 = vms1[2]
            g4 = vms1[3]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            self.create_member(pool_id=poolb['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g2.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g3.ip)

            self.create_member(pool_id=poolc['id'],
                               ip=g3.ip)
            self.create_member(pool_id=poolc['id'],
                               ip=g4.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND)
            repliesb = self.send_packets_to_vip(
                [g1, g2, g3], g_pinger, vipb['address'],
                num_packets=PACKETS_TO_SEND)
            repliesc = self.send_packets_to_vip(
                [g3, g4], g_pinger, vipc['address'],
                num_packets=PACKETS_TO_SEND)

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                total_expected=PACKETS_TO_SEND,
                identifier="poolA")
            self.check_host_replies_against_rr_baseline(
                [g1, g2, g3], repliesb,
                total_expected=PACKETS_TO_SEND,
                identifier="poolB")
            self.check_host_replies_against_rr_baseline(
                [g3, g4], repliesc,
                total_expected=PACKETS_TO_SEND,
                identifier="poolC")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
