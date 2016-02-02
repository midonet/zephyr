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

from TSM.NeutronTestCase import NeutronTestCase, GuestData, NetData, RouterData, require_extension
from collections import namedtuple
from VTM.Guest import Guest
from common.EchoServer import DEFAULT_ECHO_PORT

from tests.neutron.features.lbaas.lbaas_test_utils import *
from common.PCAPRules import *


class TestLBaaSPools(NeutronTestCase):
    """
    Test LBaaS pools.  All tests have pinger VM on its own subnet and the VIP
    on the public subnet.
    """
    def __init__(self, methodName='runTest'):
        super(TestLBaaSPools, self).__init__(methodName)

    @require_extension('lbaas')
    def test_lbaas_pools_on_start_cleanup(self):
        g_pinger = None
        g1 = None
        poola = None
        vipa = None
        member1a = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=1,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]

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

            member1a = self.api.create_member({'member': {'address': g1.ip,
                                                          'protocol_port': DEFAULT_POOL_PORT,
                                                          'pool_id': poola['id'],
                                                          'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool A: ' + str(member1a))

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            clear_lbaas_data(self, lbn_data, throw_on_fail=True)

    @require_extension('lbaas')
    def test_lbaas_pools_on_separate_subnet(self):
        g_pinger = None
        g1 = None
        g2 = None
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

            repliesa = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'])

            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa)

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)

    @require_extension('lbaas')
    def test_lbaas_pools_on_member_subnet(self):
        g_pinger = None
        g1 = None
        g2 = None
        poola = None
        vipa = None
        member1a = None
        member2a = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.22.0/24',
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

            repliesa = send_packets_to_vip(self, [g1, g2], g_pinger, vipa['address'])

            check_host_replies_against_rr_baseline(self, [g1, g2], repliesa)

        finally:
            if vipa:
                self.api.delete_vip(vipa['id'])
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)

    @require_extension('lbaas')
    def test_lbaas_pools_ignoring_vip(self):
        g_pinger = None
        g1 = None
        g2 = None
        poola = None
        member1a = None
        member2a = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.22.0/24',
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

            repliesa = send_packets_to_vip(self, [g1], g_pinger, g1.ip)
            check_host_replies_against_rr_baseline(self, [g1], repliesa)

        finally:
            if member1a:
                self.api.delete_member(member1a['id'])
            if member2a:
                self.api.delete_member(member2a['id'])
            if poola:
                self.api.delete_pool(poola['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            clear_lbaas_data(self, lbn_data)
