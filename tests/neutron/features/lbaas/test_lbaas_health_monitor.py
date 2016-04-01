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

import operator
from tests.neutron.features.lbaas.lbaas_test_utils import DEFAULT_POOL_PORT
from tests.neutron.features.lbaas.lbaas_test_utils import LBaaSTestCase
import time
from zephyr.common.cli import LinuxCLI
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm.test_case import require_topology_feature

PACKETS_TO_SEND = 30


# noinspection PyUnresolvedReferences
class TestLBaaSHealthMonitor(LBaaSTestCase):
    """
    Test health monitors in various configurations and with various parameters

    All pools have the VIP on the public subnet and the pool and members on
    separate subnets (routers)
    """
    @require_extension('lbaas')
    def test_lbaas_health_monitor_start_cleanup(self):
        try:
            self.startup_lbaas_hm_topo(num_members=1)
            time.sleep(10)
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_health_monitor_members_alive(self):
        try:
            pool1, vip1, hm1, members, vms = (
                self.startup_lbaas_hm_topo(num_members=2))
            time.sleep(10)
            g_pinger = self.create_pinger_vm()

            member1 = members[0]
            member2 = members[1]

            g1 = vms[0]
            g2 = vms[1]

            member1 = self.api.show_member(member1['id'])['member']
            member2 = self.api.show_member(member2['id'])['member']

            self.LOG.debug('Retrieved member status for member 1 in pool: ' +
                           str(member1))
            self.LOG.debug('Retrieved member status for member 2 in pool: ' +
                           str(member2))

            self.assertEqual(member1['status'], 'ACTIVE')
            self.assertEqual(member2['status'], 'ACTIVE')

            self.assertTrue(member1['admin_state_up'])
            self.assertTrue(member2['admin_state_up'])

            replies = self.send_packets_to_vip(
                [g1, g2],
                g_pinger,
                vip1['address'],
                num_packets=PACKETS_TO_SEND)
            self.check_host_replies_against_rr_baseline(
                [g1, g2],
                replies,
                total_expected=PACKETS_TO_SEND)
            self.LOG.debug("Bringing down eth0 on VM: " +
                           str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no
            # more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].down()

            time.sleep(10)

            member1 = self.api.show_member(member1['id'])['member']
            member2 = self.api.show_member(member2['id'])['member']

            self.LOG.debug('Retrieved member status for member 1 in pool: ' +
                           str(member1))
            self.LOG.debug('Retrieved member status for member 2 in pool: ' +
                           str(member2))

            # This will fail due to bug
            # https://bugs.launchpad.net/midonet/+bug/1533926
            self.ef_assertEqual(
                'https://bugs.launchpad.net/midonet/+bug/1533926',
                member1['status'], 'INACTIVE')
            self.assertEqual(member2['status'], 'ACTIVE')

            # This will fail due to bug
            # https://bugs.launchpad.net/midonet/+bug/1533926
            self.ef_assertFalse(
                'https://bugs.launchpad.net/midonet/+bug/1533926',
                member1['admin_state_up'])
            self.assertTrue(member2['admin_state_up'])

            # g1 should now receive no packets, all should go to g2
            replies = self.send_packets_to_vip(
                [g2],
                g_pinger,
                vip1['address'],
                num_packets=PACKETS_TO_SEND)
            self.check_host_replies_against_rr_baseline(
                [g2],
                replies,
                total_expected=PACKETS_TO_SEND)

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_topology_feature('compute_hosts', operator.ge, 3)
    def test_health_monitor_vm_hm_on_different_computes(self):
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
                                   name='pool1-vip1',
                                   pool_id=poola['id'])
            vipb = self.create_vip(subnet_id=self.pub_subnet['id'],
                                   protocol_port=DEFAULT_POOL_PORT + 1,
                                   name='pool1-vip1',
                                   pool_id=poolb['id'])
            g1 = self.create_member_vms(num_members=1,
                                        hv_host='cmp3')[0]
            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poolb['id'],
                               ip=g1.ip)

            hma = self.create_health_monitor()
            hmb = self.create_health_monitor()
            self.associate_health_monitor(hm_id=hma['id'],
                                          pool_id=poola['id'])
            self.associate_health_monitor(hm_id=hmb['id'],
                                          pool_id=poolb['id'])

            g_pinger = self.create_pinger_vm()

            hma_if_id = poola['id'][0:8] + '_hm_dp'
            hmb_if_id = poolb['id'][0:8] + '_hm_dp'

            self.LOG.debug("HM A interface: " + str(hma_if_id))
            self.LOG.debug("HM B interface: " + str(hmb_if_id))

            cmp1_id = LinuxCLI().cmd(
                "midonet-cli -A -e host list | grep 'cmp1' | awk '{print $2}'")

            self.LOG.debug(str(cmp1_id))
            hma_port_id = LinuxCLI().cmd(
                "midonet-cli -A -e host " + str(cmp1_id.stdout.strip()) +
                " list binding | grep '" + hma_if_id +
                "' | awk '{print $6}'")
            hmb_port_id = LinuxCLI().cmd(
                "midonet-cli -A -e host " + str(cmp1_id.stdout.strip()) +
                " list binding | grep '" + hmb_if_id +
                "' | awk '{print $6}'")

            self.LOG.debug(str(hma_port_id))
            self.LOG.debug(str(hmb_port_id))

            a = LinuxCLI().cmd("midonet-cli -A -e chain name OS_PRE_ROUTING_" +
                               self.topos['lbaas']['router']['id'] +
                               " add rule src-port 5081 in-ports " +
                               hma_port_id.stdout.strip() +
                               " pos 0 type drop")
            b = LinuxCLI().cmd("midonet-cli -A -e chain name OS_PRE_ROUTING_" +
                               self.topos['lbaas']['router']['id'] +
                               " add rule src-port 5081 in-ports " +
                               hmb_port_id.stdout.strip() +
                               " pos 0 type drop")

            self.LOG.debug(str(a))
            self.LOG.debug(str(b))

            time.sleep(10)

            repliesa = self.send_packets_to_vip(
                [g1], g_pinger, vipa['address'],
                num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT)
            repliesb = self.send_packets_to_vip(
                [g1], g_pinger, vipb['address'],
                num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT + 1)
            fail_str = ""

            try:
                self.check_host_replies_against_rr_baseline(
                    [g1], repliesa, identifier='poolA',
                    total_expected=PACKETS_TO_SEND)
            except AssertionError as e:
                fail_str += str(e) + '\n'

            try:
                self.check_host_replies_against_rr_baseline(
                    [g1], repliesb, identifier='poolB',
                    total_expected=PACKETS_TO_SEND)
            except AssertionError as e:
                fail_str += str(e) + '\n'

            if fail_str != "":
                self.fail(fail_str)
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    @require_extension('lbaas')
    def test_lbaas_health_monitor_resuscitate_members(self):
        try:
            pool1, vip1, hm1, members, vms = \
                self.startup_lbaas_hm_topo(num_members=2)
            time.sleep(10)

            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            replies = self.send_packets_to_vip(
                [g1, g2], g_pinger, vip1['address'],
                num_packets=PACKETS_TO_SEND)
            self.check_host_replies_against_rr_baseline(
                [g1, g2], replies,
                total_expected=PACKETS_TO_SEND)

            self.LOG.debug("Bringing down eth0 on VM: " +
                           str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no
            # more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].down()

            time.sleep(10)

            replies = self.send_packets_to_vip(
                [g2], g_pinger, vip1['address'],
                num_packets=PACKETS_TO_SEND)
            self.check_host_replies_against_rr_baseline(
                [g2], replies,
                total_expected=PACKETS_TO_SEND)

            self.LOG.debug("Bringing back up eth0 on VM: " +
                           str(g1.vm.vm_host.name))
            # Reinstate interface so packets can reach member again
            g1.vm.vm_host.interfaces['eth0'].up()

            time.sleep(10)

            replies = self.send_packets_to_vip(
                [g1, g2], g_pinger, vip1['address'],
                num_packets=PACKETS_TO_SEND)
            self.check_host_replies_against_rr_baseline(
                [g1, g2], replies,
                total_expected=PACKETS_TO_SEND)
        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()

    def startup_lbaas_hm_topo(self, num_members=2):
        self.create_member_net()
        self.create_lbaas_net()
        self.create_pinger_net()
        self.create_lb_router(gw_net_id=self.pub_network['id'])

        pool1 = self.create_pool(
            subnet_id=self.topos['main']['lbaas']['subnet']['id'])

        vip1 = self.create_vip(subnet_id=self.pub_subnet['id'],
                               name='pool1-vip1',
                               pool_id=pool1['id'])
        members = []
        vms = self.create_member_vms(num_members=num_members)
        for i in vms:
            members.append(self.create_member(pool_id=pool1['id'],
                                              ip=i.ip))

        hm = self.create_health_monitor()
        self.associate_health_monitor(hm_id=hm['id'],
                                      pool_id=pool1['id'])

        self.assertEqual(num_members, len(self.member_ids))
        self.assertEqual(num_members, len(members))
        self.assertEqual(num_members, len(vms))
        self.assertEqual(1, len(self.pool_ids))
        self.assertEqual(1, len(self.vip_ids))
        self.assertEqual(1, len(self.health_monitor_ids))
        self.assertEqual(1, len(self.associated_health_monitors))
        return pool1, vip1, hm, members, vms
