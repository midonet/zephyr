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
import time

from TSM.NeutronTestCase import NeutronTestCase, GuestData, NetData, RouterData, require_extension
from TSM.TestCase import require_topology_feature, expected_failure
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.host.Host import Host

from collections import namedtuple
from common.EchoServer import DEFAULT_ECHO_PORT
from common.CLI import LinuxCLI

from tests.neutron.features.lbaas.lbaas_test_utils import *

PACKETS_TO_SEND = 30


class TestLBaaSHealthMonitor(NeutronTestCase):
    """
    Test health monitors in various configurations and with various parameters

    All pools have the VIP on the public subnet and the pool and members on separate
    subnets (routers)
    """
    def __init__(self, methodName='runTest'):
        super(TestLBaaSHealthMonitor, self).__init__(methodName)

    @require_extension('lbaas')
    def test_lbaas_health_monitor_start_cleanup(self):
        delay = 3
        timeout = 1
        pool1 = None
        vip1 = None
        member1 = None
        lbn_data = None
        hm = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=1,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))

            hm = self.api.create_health_monitor({'health_monitor': {'tenant_id': 'admin',
                                                                    'type': 'TCP',
                                                                    'delay': delay,
                                                                    'timeout': timeout,
                                                                    'max_retries': 2}})['health_monitor']
            self.api.associate_health_monitor(pool1['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hm['id']}})
            hm = self.api.show_health_monitor(hm['id'])['health_monitor']
            self.LOG.debug("Created Health Monitor and associated to pool: " + str(hm))

            time.sleep(delay * 3)

        finally:
            if hm:
                self.api.disassociate_health_monitor(pool1['id'], hm['id'])
                self.api.delete_health_monitor(hm['id'])
            if vip1:
                self.api.delete_vip(vip1['id'])
            if member1:
                self.api.delete_member(member1['id'])
            if pool1:
                self.api.delete_pool(pool1['id'])
            clear_lbaas_data(self, lbn_data, throw_on_fail=True)

    @require_extension('lbaas')
    def test_lbaas_health_monitor_members_alive(self):
        delay = 3
        timeout = 1
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        hm = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            member2 = self.api.create_member({'member': {'address': g2.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2))

            hm = self.api.create_health_monitor({'health_monitor': {'tenant_id': 'admin',
                                                                    'type': 'TCP',
                                                                    'delay': delay,
                                                                    'timeout': timeout,
                                                                    'max_retries': 2}})['health_monitor']
            self.api.associate_health_monitor(pool1['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hm['id']}})
            hm = self.api.show_health_monitor(hm['id'])['health_monitor']
            self.LOG.debug("Created Health Monitor and associated to pool: " + str(hm))

            time.sleep(delay * 3)

            member1 = self.api.show_member(member1['id'])['member']
            member2 = self.api.show_member(member2['id'])['member']

            self.LOG.debug('Retrieved member status for member 1 in pool: ' + str(member1))
            self.LOG.debug('Retrieved member status for member 2 in pool: ' + str(member2))

            self.assertEqual(member1['status'], 'ACTIVE')
            self.assertEqual(member2['status'], 'ACTIVE')

            self.assertTrue(member1['admin_state_up'])
            self.assertTrue(member2['admin_state_up'])

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies,
                                                   total_expected=PACKETS_TO_SEND)

            self.LOG.debug("Bringing down eth0 on VM: " + str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].down()

            time.sleep(delay * 3)

            member1 = self.api.show_member(member1['id'])['member']
            member2 = self.api.show_member(member2['id'])['member']

            self.LOG.debug('Retrieved member status for member 1 in pool: ' + str(member1))
            self.LOG.debug('Retrieved member status for member 2 in pool: ' + str(member2))

            # This will fail due to bug https://bugs.launchpad.net/midonet/+bug/1533926
            self.ef_assertEqual('https://bugs.launchpad.net/midonet/+bug/1533926',
                                member1['status'], 'INACTIVE')
            self.assertEqual(member2['status'], 'ACTIVE')

            # This will fail due to bug https://bugs.launchpad.net/midonet/+bug/1533926
            self.ef_assertFalse('https://bugs.launchpad.net/midonet/+bug/1533926',
                                member1['admin_state_up'])
            self.assertTrue(member2['admin_state_up'])

            # g1 should now receive no packets, all should go to g2
            replies = send_packets_to_vip(self, [g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g2], replies,
                                                   total_expected=PACKETS_TO_SEND)

        finally:
            if hm:
                self.api.disassociate_health_monitor(pool1['id'], hm['id'])
                self.api.delete_health_monitor(hm['id'])
            if vip1:
                self.api.delete_vip(vip1['id'])
            if member1:
                self.api.delete_member(member1['id'])
            if member2:
                self.api.delete_member(member2['id'])
            if pool1:
                self.api.delete_pool(pool1['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)

    @require_topology_feature('compute_hosts', operator.ge, 3)
    def test_health_monitor_vm_hm_on_different_computes(self):
        delay = 3
        timeout = 1

        g1 = None
        g_pinger = None
        poola = None
        poolb = None
        vipa = None
        vipb = None
        member1a = None
        member1b = None
        lbn_data = None
        hma = None
        hmb = None

        hma_if_id = None
        hmb_if_id = None

        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=0,
                                            create_pinger_net=True)

            port_g1 = self.api.create_port({'port': {'name': 'port1',
                                                     'network_id': lbn_data.member.network['id'],
                                                     'admin_state_up': True,
                                                     'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas member a1: ' + str(port_g1))

            ip_g1 = port_g1['fixed_ips'][0]['ip_address']
            vm_g1 = self.vtm.create_vm(ip=ip_g1, mac=port_g1['mac_address'],
                                       gw_ip=lbn_data.member.subnet['gateway_ip'],
                                       hv_host="cmp3")
            vm_g1.plugin_vm('eth0', port_g1['id'])
            g1 = GuestData(port_g1, vm_g1, ip_g1)

            port_g_pinger = self.api.create_port({'port': {'name': 'port_pinger',
                                                           'network_id': lbn_data.pinger.network['id'],
                                                           'admin_state_up': True,
                                                           'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for pinger: ' + str(port_g_pinger))

            ip_g_pinger = port_g_pinger['fixed_ips'][0]['ip_address']
            vm_g_pinger = self.vtm.create_vm(ip=ip_g_pinger, mac=port_g_pinger['mac_address'],
                                             gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_g_pinger.plugin_vm('eth0', port_g_pinger['id'])
            g_pinger = GuestData(port_g_pinger, vm_g_pinger, ip_g_pinger)

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'poola-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poola['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP A: ' + str(vipa))

            poolb = self.api.create_pool({'pool': {'name': 'poolb',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool B: ' + str(poolb))

            vipb = self.api.create_vip({'vip': {'name': 'poolb-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT + 1,
                                                'pool_id': poolb['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP B: ' + str(vipb))

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))

            member1b = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT + 1,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member2 for LBaaS Pool A: ' + str(member1b))

            hma = self.api.create_health_monitor({'health_monitor': {'tenant_id': 'admin',
                                                                     'type': 'TCP',
                                                                     'delay': delay,
                                                                     'timeout': timeout,
                                                                     'max_retries': 2}})['health_monitor']
            self.api.associate_health_monitor(poola['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hma['id']}})
            hma = self.api.show_health_monitor(hma['id'])['health_monitor']
            self.LOG.debug("Created Health Monitor A and associated to pool A: " + str(hma))

            hmb = self.api.create_health_monitor({'health_monitor': {'tenant_id': 'admin',
                                                                     'type': 'TCP',
                                                                     'delay': delay,
                                                                     'timeout': timeout,
                                                                     'max_retries': 2}})['health_monitor']
            self.api.associate_health_monitor(poolb['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hmb['id']}})
            hmb = self.api.show_health_monitor(hmb['id'])['health_monitor']
            self.LOG.debug("Created Health Monitor B and associated to pool B: " + str(hmb))

            hma_if_id = poola['id'][0:8] + '_hm_dp'
            hmb_if_id = poolb['id'][0:8] + '_hm_dp'

            print "HM A interface: " + str(hma_if_id)
            print "HM B interface: " + str(hmb_if_id)

            cmp1_id = LinuxCLI().cmd("midonet-cli -A -e host list | grep 'cmp1' | awk '{print $2}'")

            print str(cmp1_id)
            hma_port_id = LinuxCLI().cmd("midonet-cli -A -e host " + str(cmp1_id.stdout.strip()) +
                                         " list binding | grep '" + hma_if_id +
                                         "' | awk '{print $6}'")
            hmb_port_id = LinuxCLI().cmd("midonet-cli -A -e host " + str(cmp1_id.stdout.strip()) +
                                         " list binding | grep '" + hmb_if_id +
                                         "' | awk '{print $6}'")

            print str(hma_port_id)
            print str(hmb_port_id)

            a = LinuxCLI().cmd("midonet-cli -A -e chain name OS_PRE_ROUTING_" +
                               lbn_data.router.router['id'] +
                               " add rule src-port 5081 in-ports " + hma_port_id.stdout.strip() +
                               " pos 0 type drop")
            b = LinuxCLI().cmd("midonet-cli -A -e chain name OS_PRE_ROUTING_" +
                               lbn_data.router.router['id'] +
                               " add rule src-port 5081 in-ports " + hmb_port_id.stdout.strip() +
                               " pos 0 type drop")

            print str(a)
            print str(b)

            time.sleep(delay * 3)

            member1a = self.api.show_member(member1a['id'])['member']
            member1b = self.api.show_member(member1b['id'])['member']

            self.LOG.debug('Retrieved member status for member1 in pool A: ' + str(member1a))
            self.LOG.debug('Retrieved member status for member1 in pool B: ' + str(member1b))

            self.assertEqual(member1a['status'], 'ACTIVE')
            self.assertEqual(member1b['status'], 'ACTIVE')

            self.assertTrue(member1a['admin_state_up'])
            self.assertTrue(member1b['admin_state_up'])

            repliesa = send_packets_to_vip(self, [g1], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT)
            repliesb = send_packets_to_vip(self, [g1], g_pinger, vipb['address'],
                                           num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT + 1)
            fail_str = ""
            try:
                check_host_replies_against_rr_baseline(self, [g1], repliesa, identifier='poolA',
                                                       total_expected=PACKETS_TO_SEND)
            except AssertionError as e:
                fail_str += str(e) + '\n'

            try:
                check_host_replies_against_rr_baseline(self, [g1], repliesb, identifier='poolB',
                                                       total_expected=PACKETS_TO_SEND)
            except AssertionError as e:
                fail_str += str(e) + '\n'

            if fail_str != "":
                self.fail(fail_str)

        finally:
            cleanup_fail = False
            try:
                if hma:
                    self.LOG.debug("Deleting health monitor: " + hma['id'])
                    self.api.disassociate_health_monitor(poola['id'], hma['id'])
                    self.api.delete_health_monitor(hma['id'])
                if hmb:
                    self.LOG.debug("Deleting health monitor: " + hmb['id'])
                    self.api.disassociate_health_monitor(poolb['id'], hmb['id'])
                    self.api.delete_health_monitor(hmb['id'])
                if vipa:
                    self.LOG.debug("Deleting VIP: " + vipa['id'])
                    self.api.delete_vip(vipa['id'])
                if member1a:
                    self.LOG.debug("Deleting member: " + member1a['id'])
                    self.api.delete_member(member1a['id'])
                if poola:
                    self.LOG.debug("Deleting pool: " + poola['id'])
                    self.api.delete_pool(poola['id'])
                if vipb:
                    self.LOG.debug("Deleting VIP: " + vipb['id'])
                    self.api.delete_vip(vipb['id'])
                if member1b:
                    self.LOG.debug("Deleting member: " + member1b['id'])
                    self.api.delete_member(member1b['id'])
                if poolb:
                    self.LOG.debug("Deleting pool: " + poolb['id'])
                    self.api.delete_pool(poolb['id'])
            except Exception as e:
                self.LOG.fatal("Error cleaning test topology: " + str(e))
                cleanup_fail = True

            try:
                self.cleanup_vms([(g1.vm, g1.port), (g_pinger.vm, g_pinger.port)])
            except Exception as e:
                self.LOG.fatal("Error cleaning VMs: " + str(e))
                cleanup_fail = True

            clear_lbaas_data(self, lbn_data)

            if cleanup_fail:
                self.fail("Failed cleaning up test topology")

    @require_extension('lbaas')
    def test_lbaas_health_monitor_resuscitate_members(self):
        delay = 3
        timeout = 1
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        hm = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            member2 = self.api.create_member({'member': {'address': g2.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2))

            hm = self.api.create_health_monitor({'health_monitor': {'tenant_id': 'admin',
                                                                    'type': 'TCP',
                                                                    'delay': delay,
                                                                    'timeout': timeout,
                                                                    'max_retries': 2}})['health_monitor']
            self.api.associate_health_monitor(pool1['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hm['id']}})
            hm = self.api.show_health_monitor(hm['id'])['health_monitor']
            self.LOG.debug("Created Health Monitor and associated to pool: " + str(hm))

            time.sleep(delay * 3)

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies,
                                                   total_expected=PACKETS_TO_SEND)

            self.LOG.debug("Bringing down eth0 on VM: " + str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].down()

            time.sleep(delay * 3)

            # g1 should now receive no packets, all should go to g2
            replies = send_packets_to_vip(self, [g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g2], replies,
                                                   total_expected=PACKETS_TO_SEND)

            self.LOG.debug("Bringing back up eth0 on VM: " + str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].up()

            time.sleep(delay * 3)

            # g1 should now again receive packets
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies,
                                                   total_expected=PACKETS_TO_SEND)

        finally:
            if hm:
                self.api.disassociate_health_monitor(pool1['id'], hm['id'])
                self.api.delete_health_monitor(hm['id'])
            if vip1:
                self.api.delete_vip(vip1['id'])
            if member1:
                self.api.delete_member(member1['id'])
            if member2:
                self.api.delete_member(member2['id'])
            if pool1:
                self.api.delete_pool(pool1['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)

