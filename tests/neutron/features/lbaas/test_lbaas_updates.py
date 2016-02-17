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

from TSM.NeutronTestCase import GuestData
from TSM.NeutronTestCase import NeutronTestCase
from TSM.NeutronTestCase import require_extension

from tests.neutron.features.lbaas.lbaas_test_utils import *

PACKETS_TO_SEND = 40


class TestLBaaSUpdates(NeutronTestCase):
    def __init__(self, methodName='runTest'):
        super(TestLBaaSUpdates, self).__init__(methodName)

    @require_extension('lbaas')
    def test_lbaas_delete_members(self):
        g_pinger = None
        poola = None
        vipa = None
        member1a = None
        member2a = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port_pinger',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)
            """ :type: GuestData """

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poola['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP A: ' + str(vipa))

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1a))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2a))

            repliesa = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa,
                                                   total_expected=PACKETS_TO_SEND)

            self.api.delete_member(member1a['id'])
            member1a = None

            repliesb = send_packets_to_vip(self, [g2], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g2], repliesb,
                                                   total_expected=PACKETS_TO_SEND)

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            clear_lbaas_data(self, lbn_data)
            self.cleanup_vms([(g_pinger.vm, g_pinger.port)])

    @require_extension('lbaas')
    def test_lbaas_delete_readd_members(self):
        g_pinger = None
        poola = None
        vipa = None
        member1a = None
        member2a = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port_pinger',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)
            """ :type: GuestData """

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

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1a for LBaaS Pool: ' + str(member1a))
            self.LOG.debug('Created member2a for LBaaS Pool: ' + str(member2a))

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'])
            check_host_replies_against_rr_baseline(self, [g1, g2], replies)

            self.api.delete_member(member1a['id'])
            member1a = None

            repliesa = send_packets_to_vip(self, [g2], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g2], repliesa,
                                                   total_expected=PACKETS_TO_SEND)

            self.assertFalse(g1.vm.vm_host.name in repliesa)

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            repliesb = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], repliesb,
                                                   total_expected=PACKETS_TO_SEND)

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            clear_lbaas_data(self, lbn_data)
            self.cleanup_vms([(g_pinger.vm, g_pinger.port)])

    @require_extension('lbaas')
    def test_lbaas_update_pools_switch_subnet(self):
        g_pingera = None
        g_pingerb = None
        poola = None
        vipa = None
        member1a = None
        member2a = None
        lbn_data = None
        lbn_data2 = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True,
                                            pinger_cidr='192.168.55.0/24')
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            lbn_data2 = create_lb_member_net(self, lbaas_cidr='192.168.77.0/24',
                                             member_cidr='192.168.77.0/24',
                                             num_members=0,
                                             create_pinger_net=True,
                                             pinger_cidr='192.168.88.0/24')

            port_pingera = self.api.create_port({'port': {'name': 'port_pingera',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger A: ' + str(port_pingera))

            ip_pingera = port_pingera['fixed_ips'][0]['ip_address']
            vm_pingera = self.vtm.create_vm(ip=ip_pingera, mac=port_pingera['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pingera.plugin_vm('eth0', port_pingera['id'])
            g_pingera = GuestData(port_pingera, vm_pingera, ip_pingera)
            """ :type: GuestData """

            port_pingerb = self.api.create_port({'port': {'name': 'port_pingerb',
                                                         'network_id': lbn_data2.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger B: ' + str(port_pingerb))

            ip_pingerb = port_pingerb['fixed_ips'][0]['ip_address']
            vm_pingerb = self.vtm.create_vm(ip=ip_pingerb, mac=port_pingerb['mac_address'],
                                           gw_ip=lbn_data2.pinger.subnet['gateway_ip'])
            vm_pingerb.plugin_vm('eth0', port_pingerb['id'])
            g_pingerb = GuestData(port_pingerb, vm_pingerb, ip_pingerb)
            """ :type: GuestData """

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lbn_data.pinger.subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poola['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP A: ' + str(vipa))

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))
            self.LOG.debug('Created member2 for LBaaS Pool A: ' + str(member2a))
            repliesa = send_packets_to_vip(self, [g1, g2], g_pingera, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa,
                                                   total_expected=PACKETS_TO_SEND)

            poola = self.api.update_pool(
                    poola['id'],
                    {'pool': {'subnet_id': lbn_data2.lbaas.subnet['id']}})['pool']

            repliesb = send_packets_to_vip(self, [g1, g2], g_pingerb, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], repliesb,
                                                   total_expected=PACKETS_TO_SEND)

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            clear_lbaas_data(self, lbn_data)
            clear_lbaas_data(self, lbn_data2)
            if g_pingera:
                self.cleanup_vms([(g_pingera.vm, g_pingera.port)])
            if g_pingerb:
                self.cleanup_vms([(g_pingerb.vm, g_pingerb.port)])

    @require_extension('lbaas')
    def test_lbaas_update_members_switch_pools(self):
        g_pinger = None
        poola = None
        vipa = None
        poolb = None
        vipb = None
        member1a = None
        member2a = None
        member2b = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=3,
                                            create_pinger_net=True,
                                            pinger_cidr='192.168.55.0/24')
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]
            g3 = lbn_data.member_vms[2]

            port_pinger = self.api.create_port({'port': {'name': 'port_pinger',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)
            """ :type: GuestData """

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
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poolb['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP B: ' + str(vipb))

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2b = self.api.create_member({'member': {'address': g3.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))
            self.LOG.debug('Created member2 for LBaaS Pool A: ' + str(member2a))
            self.LOG.debug('Created member2 for LBaaS Pool B: ' + str(member2b))
            repliesa1 = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'],
                                            num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa1,
                                                   total_expected=PACKETS_TO_SEND, identifier='poolA')
            repliesa2 = send_packets_to_vip(self, [g3], g_pinger, vipb['address'],
                                            num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g3], repliesa2,
                                                   total_expected=PACKETS_TO_SEND, identifier='poolB')

            member1a = self.api.update_member(member1a['id'],
                                              {'member': {'pool_id': poolb['id']}})['member']

            self.LOG.debug('Updated member1 to LBaaS Pool B: ' + str(member1a))
            repliesb1 = send_packets_to_vip(self, [g2], g_pinger, vipa['address'],
                                            num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g2], repliesb1,
                                                   total_expected=PACKETS_TO_SEND, identifier='poolA')
            repliesb2 = send_packets_to_vip(self, [g1, g3], g_pinger, vipa['address'],
                                            num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g3], repliesb2,
                                                   total_expected=PACKETS_TO_SEND, identifier='poolB')

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            if vipb:
                self.api.delete_vip(vipb['id'])
            if member2b:
                self.api.delete_member(member2b['id'])
            if poolb:
                self.api.delete_pool(poolb['id'])
            clear_lbaas_data(self, lbn_data)
            self.cleanup_vms([(g_pinger.vm, g_pinger.port)])

    @require_extension('lbaas')
    def test_lbaas_update_hm_disassociate_kill_member_reassociate(self):
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

            self.api.disassociate_health_monitor(pool1['id'], hm['id'])

            self.LOG.debug("Bringing down eth0 on VM: " + str(g1.vm.vm_host.name))
            # Kill one member's TCP interface and make sure no more packets get sent there
            g1.vm.vm_host.interfaces['eth0'].down()

            time.sleep(delay * 3)

            # Without HM, it should try (and fail) to send some to g1
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            num_misses = replies['NO_RESPONSE']
            num_g1_hits = replies[g1.vm.vm_host.name]
            num_g2_hits = replies[g2.vm.vm_host.name]
            self.assertEqual(PACKETS_TO_SEND - num_g2_hits, num_misses)
            self.assertEqual(0, num_g1_hits)

            self.api.associate_health_monitor(pool1['id'], {'health_monitor': {'tenant_id': 'admin',
                                                                               'id': hm['id']}})

            time.sleep(delay * 3)

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
