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


class TestLBaaSPools(LBaaSTestCase):
    """
    Test LBaaS pools.  All tests have pinger VM on its own subnet and the VIP
    on the public subnet.
    """

    @require_extension('lbaas')
    def test_lbaas_pools_on_start_cleanup(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vms = self.create_member_vms(num_members=1)
            g1 = vms[0]

            self.create_member(pool_id=poola['id'],
                               ip_addr=g1.ip)
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_pools_on_separate_subnet(self):
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

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'])

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                identifier="poolA")

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_pools_on_member_subnet(self):
        try:
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT,
                                   name='poola-vip1',
                                   pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2, net='lbaas')
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1, g2], g_pinger, vipa['address'])

            self.check_host_replies_against_rr_baseline(
                [g1, g2], repliesa,
                identifier="poolA")
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_pools_ignoring_vip(self):
        try:

            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vms = self.create_member_vms(num_members=2, net='lbaas')
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip_addr=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip_addr=g2.ip)

            repliesa = self.send_packets_to_vip(
                [g1], g_pinger, g1.ip)

            self.check_host_replies_against_rr_baseline(
                [g1], repliesa)

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
