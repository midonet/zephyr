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
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm.test_case import expected_failure

PACKETS_TO_SEND = 30


class TestLBaaSVIP(NeutronTestCase):
    def __init__(self, methodName='runTest'):
        super(TestLBaaSVIP, self).__init__(methodName)

    @require_extension('lbaas')
    def test_lbaas_vip_on_pool_subnet_pinger_on_pinger_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
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
            """ :type: GuestData """

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lbn_data.lbaas.subnet['id'],
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
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)
        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_member_subnet_pinger_on_pinger_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
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
            """ :type: GuestData """

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lbn_data.member.subnet['id'],
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
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)
        finally:
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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_pinger_subnet_pinger_on_pinger_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
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
            """ :type: GuestData """

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lbn_data.pinger.subnet['id'],
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
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)
        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_pinger_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
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
            """ :type: GuestData """

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
            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)
        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_pool_subnet_pinger_on_member_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.member.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.member.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.lbaas.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_member_subnet_pinger_on_member_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.member.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.member.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.member.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_isolated_subnet_pinger_on_member_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.member.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.member.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.pinger.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_member_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.member.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.member.subnet['gateway_ip'],
                                           name='vm_pinger')
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    @expected_failure('https://bugs.launchpad.net/midonet/+bug/1533437')
    def test_lbaas_vip_on_pool_subnet_pinger_on_pool_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.lbaas.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.lbaas.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.lbaas.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_member_subnet_pinger_on_pool_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.lbaas.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.lbaas.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.member.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_isolated_subnet_pinger_on_pool_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.lbaas.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.lbaas.subnet['gateway_ip'],
                                           name='vm_pinger')
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
                                                'subnet_id': lbn_data.pinger.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_on_public_subnet_pinger_on_pool_subnet(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=2,
                                            create_pinger_net=False)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': lbn_data.lbaas.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=lbn_data.lbaas.subnet['gateway_ip'],
                                           name='vm_pinger')
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

        finally:
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

    @require_extension('lbaas')
    def test_lbaas_vip_add_member(self):
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        lbn_data = None
        try:
            lbn_data = create_lb_member_net(self, lbaas_cidr='192.168.22.0/24',
                                            member_cidr='192.168.33.0/24',
                                            num_members=3,
                                            create_pinger_net=True)
            g1 = lbn_data.member_vms[0]
            g2 = lbn_data.member_vms[1]
            g3 = lbn_data.member_vms[2]

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

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lbn_data.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lbn_data.lbaas.subnet['id'],
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

            replies = send_packets_to_vip(self, [g1, g2], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2], replies, total_expected=PACKETS_TO_SEND)

            member3 = self.api.create_member({'member': {'address': g3.ip,
                                                         'protocol_port': DEFAULT_POOL_PORT,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            self.LOG.debug('Created member3 for LBaaS Pool: ' + str(member3))
            replies = send_packets_to_vip(self, [g1, g2, g3], g_pinger, vip1['address'],
                                          num_packets=PACKETS_TO_SEND)
            check_host_replies_against_rr_baseline(self, [g1, g2, g3], replies, total_expected=PACKETS_TO_SEND)

        finally:
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
