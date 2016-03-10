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


class TestLBaaSMultiplePools(NeutronTestCase):
    """
    Test LBaaS multiple pools.  All tests have pinger VM on its own subnet and the VIP
    on the public subnet.
    """
    def __init__(self, methodName='runTest'):
        super(TestLBaaSMultiplePools, self).__init__(methodName)

    @require_extension('lbaas')
    def test_lbaas_multiple_pools_same_subnet(self):
        g_pinger = None
        poola = None
        poolb = None
        vipa = None
        vipb = None
        member1a = None
        member2a = None
        member1b = None
        member2b = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=4,
                                            create_pinger_net=True)
            g1a = lbn_data.member_vms[0]
            g2a = lbn_data.member_vms[1]
            g1b = lbn_data.member_vms[2]
            g2b = lbn_data.member_vms[3]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.pinger.subnet['gateway_ip'],
                                           name='vm_pinger')
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'poola-vip',
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

            vipb = self.api.create_vip({'vip': {'name': 'poolb-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poolb['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP B: ' + str(vipb))

            member1a = self.api.create_member({'member': {'address': g1a.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2a.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))
            self.LOG.debug('Created member2 for LBaaS Pool A: ' + str(member2a))

            member1b = self.api.create_member({'member': {'address': g1b.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2b = self.api.create_member({'member': {'address': g2b.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool B: ' + str(member1b))
            self.LOG.debug('Created member2 for LBaaS Pool B: ' + str(member2b))

            repliesa = send_packets_to_vip(self, [g1a, g2a], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            repliesb = send_packets_to_vip(self, [g1b, g2b], g_pinger, vipb['address'],
                                           num_packets=PACKETS_TO_SEND)

            check_host_replies_against_rr_baseline(self, [g1a, g2a], repliesa,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolA")
            check_host_replies_against_rr_baseline(self, [g1b, g2b], repliesb,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolB")

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
            if member1b:
                self.api.delete_member(member1b['id'])
            if member2b:
                self.api.delete_member(member2b['id'])
            if poolb:
                self.api.delete_pool(poolb['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)

    @require_extension('lbaas')
    def test_lbaas_multiple_pools_multiple_subnets(self):
        g_pingera = None
        g_pingerb = None
        poola = None
        poolb = None
        vipa = None
        vipb = None
        member1a = None
        member2a = None
        member1b = None
        member2b = None
        lbn_dataa = None
        lbn_datab = None
        try:
            lbn_dataa = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                             member_cidr='192.168.33.0/24',
                                             num_members=2,
                                             create_pinger_net=True,
                                             pinger_cidr='192.168.55.0/24')
            lbn_datab = create_lb_member_net(self, lbaas_cidr='192.168.66.0/24',
                                             member_cidr='192.168.77.0/24',
                                             num_members=2,
                                             create_pinger_net=True,
                                             pinger_cidr='192.168.88.0/24')
            g1a = lbn_dataa.member_vms[0]
            g2a = lbn_dataa.member_vms[1]
            g1b = lbn_datab.member_vms[0]
            g2b = lbn_datab.member_vms[1]

            port_pingera = self.api.create_port({'port': {'name': 'port_pingera',
                                                          'network_id': lbn_dataa.pinger.network['id'],
                                                          'admin_state_up': True,
                                                          'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger A: ' + str(port_pingera))

            ip_pingera = port_pingera['fixed_ips'][0]['ip_address']
            vm_pingera = self.vtm.create_vm(ip=ip_pingera, mac=port_pingera['mac_address'],
                                            gw_ip=lbn_dataa.pinger.subnet['gateway_ip'],
                                            name='vm_pinger')
            vm_pingera.plugin_vm('eth0', port_pingera['id'])
            g_pingera = GuestData(port_pingera, vm_pingera, ip_pingera)

            port_pingerb = self.api.create_port({'port': {'name': 'port_pingerb',
                                                          'network_id': lbn_datab.pinger.network['id'],
                                                          'admin_state_up': True,
                                                          'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger B: ' + str(port_pingerb))

            ip_pingerb = port_pingerb['fixed_ips'][0]['ip_address']
            vm_pingerb = self.vtm.create_vm(ip=ip_pingerb, mac=port_pingerb['mac_address'],
                                            gw_ip=lbn_datab.pinger.subnet['gateway_ip'],
                                            name='vm_pingerb')
            vm_pingerb.plugin_vm('eth0', port_pingerb['id'])
            g_pingerb = GuestData(port_pingerb, vm_pingerb, ip_pingerb)

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_dataa.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'poola-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poola['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP A: ' + str(vipa))

            poolb = self.api.create_pool({'pool': {'name': 'poolb',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_datab.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool B: ' + str(poolb))

            vipb = self.api.create_vip({'vip': {'name': 'poolb-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT + 1,
                                                'pool_id': poolb['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP B: ' + str(vipb))

            member1a = self.api.create_member({'member': {'address': g1a.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2a = self.api.create_member({'member': {'address': g2a.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))
            self.LOG.debug('Created member2 for LBaaS Pool A: ' + str(member2a))

            member1b = self.api.create_member({'member': {'address': g1b.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT + 1,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2b = self.api.create_member({'member': {'address': g2b.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT + 1,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool B: ' + str(member1b))
            self.LOG.debug('Created member2 for LBaaS Pool B: ' + str(member2b))

            repliesa = send_packets_to_vip(self, [g1a, g2a], g_pingera, vipa['address'],
                                           num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT)
            repliesb = send_packets_to_vip(self, [g1b, g2b], g_pingerb, vipb['address'],
                                           num_packets=PACKETS_TO_SEND, to_port=DEFAULT_POOL_PORT + 1)

            check_host_replies_against_rr_baseline(self, [g1a, g2a], repliesa,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolA")
            check_host_replies_against_rr_baseline(self, [g1b, g2b], repliesb,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolB")

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
            if member1b:
                self.api.delete_member(member1b['id'])
            if member2b:
                self.api.delete_member(member2b['id'])
            if poolb:
                self.api.delete_pool(poolb['id'])
            if g_pingera:
                self.cleanup_vms([(g_pingera.vm, g_pingera.port)])
            if g_pingerb:
                self.cleanup_vms([(g_pingerb.vm, g_pingerb.port)])
            clear_lbaas_data(self, lbn_dataa)
            clear_lbaas_data(self, lbn_datab)

    @require_extension('lbaas')
    def test_lbaas_multiple_pools_shared_members(self):
        g_pinger = None
        poola = None
        poolb = None
        poolc = None
        vipa = None
        vipb = None
        vipc = None
        member1a = None
        member2a = None
        member1b = None
        member2b = None
        member3b = None
        member1c = None
        member2c = None
        lbn_dataa = None
        try:
            lbn_dataa = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                             member_cidr='192.168.33.0/24',
                                             num_members=4,
                                             create_pinger_net=True,
                                             pinger_cidr='192.168.55.0/24')
            g1 = lbn_dataa.member_vms[0]
            g2 = lbn_dataa.member_vms[1]
            g3 = lbn_dataa.member_vms[2]
            g4 = lbn_dataa.member_vms[3]

            port_pinger = self.api.create_port({'port': {'name': 'port_pinger',
                                                         'network_id': lbn_dataa.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_dataa.pinger.subnet['gateway_ip'],
                                           name='vm_pinger')
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            poola = self.api.create_pool({'pool': {'name': 'poola',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_dataa.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool A: ' + str(poola))

            vipa = self.api.create_vip({'vip': {'name': 'poola-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poola['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP A: ' + str(vipa))

            poolb = self.api.create_pool({'pool': {'name': 'poolb',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_dataa.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool B: ' + str(poolb))

            vipb = self.api.create_vip({'vip': {'name': 'poolb-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poolb['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP B: ' + str(vipb))

            poolc = self.api.create_pool({'pool': {'name': 'poolc',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_dataa.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool C: ' + str(poolc))

            vipc = self.api.create_vip({'vip': {'name': 'poolc-vip',
                                                'subnet_id': self.pub_subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': DEFAULT_POOL_PORT,
                                                'pool_id': poolc['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP C: ' + str(vipc))

            # Pool A members
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

            # Pool B members
            member1b = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2b = self.api.create_member({'member': {'address': g2.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']
            member3b = self.api.create_member({'member': {'address': g3.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolb['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool B: ' + str(member1b))
            self.LOG.debug('Created member2 for LBaaS Pool B: ' + str(member2b))
            self.LOG.debug('Created member3 for LBaaS Pool B: ' + str(member3b))

            # Pool C members
            member1c = self.api.create_member({'member': {'address': g3.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolc['id'],
                                                          'tenant_id': 'admin'}})['member']
            member2c = self.api.create_member({'member': {'address': g4.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poolc['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool C: ' + str(member1c))
            self.LOG.debug('Created member2 for LBaaS Pool C: ' + str(member2c))

            repliesa = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'],
                                           num_packets=PACKETS_TO_SEND)
            repliesb = send_packets_to_vip(self, [g1, g2, g3], g_pinger, vipb['address'],
                                           num_packets=PACKETS_TO_SEND)
            repliesc = send_packets_to_vip(self, [g3, g4], g_pinger, vipc['address'],
                                           num_packets=PACKETS_TO_SEND)

            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolA")
            check_host_replies_against_rr_baseline(self, [g1, g2, g3], repliesb,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolB")
            check_host_replies_against_rr_baseline(self, [g3, g4], repliesc,
                                                   total_expected=PACKETS_TO_SEND,
                                                   identifier="poolC")

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
            if member1b:
                self.api.delete_member(member1b['id'])
            if member2b:
                self.api.delete_member(member2b['id'])
            if member3b:
                self.api.delete_member(member3b['id'])
            if poolb:
                self.api.delete_pool(poolb['id'])
            if vipc:
                self.api.delete_vip(vipc['id'])
            if member1c:
                self.api.delete_member(member1c['id'])
            if member2c:
                self.api.delete_member(member2c['id'])
            if poolc:
                self.api.delete_pool(poolc['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_dataa)
