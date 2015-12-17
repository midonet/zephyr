__author__ = 'micucci'
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

TopoData = namedtuple('TopoData', 'member lbaas pinger router guest1 guest2')

NUM_PACKETS_TO_SEND = 50


class TestLBaaSRoundRobin(NeutronTestCase):
    def __init__(self, methodName='runTest'):
        super(TestLBaaSRoundRobin, self).__init__(methodName)

    def create_lbaas_network_topology(self):
        try:
            member_net = self.api.create_network({'network': {'name': 'member_net',
                                                              'tenant_id': 'admin'}})['network']
            member_subnet = self.api.create_subnet({'subnet': {'name': 'member_sub',
                                                               'network_id': member_net['id'],
                                                               'ip_version': 4, 'cidr': '192.168.22.0/24',
                                                               'tenant_id': 'admin'}})['subnet']

            self.LOG.debug('Created subnet for member pool: ' + str(member_subnet))

            lbaas_net = self.api.create_network({'network': {'name': 'lbaas_net',
                                                             'tenant_id': 'admin'}})['network']
            lbaas_subnet = self.api.create_subnet({'subnet': {'name': 'lbaas_sub',
                                                              'network_id': lbaas_net['id'],
                                                              'ip_version': 4, 'cidr': '192.168.55.0/24',
                                                              'tenant_id': 'admin'}})['subnet']

            self.LOG.debug('Created subnet for LBaaS pool: ' + str(lbaas_subnet))

            pinger_net = self.api.create_network({'network': {'name': 'pinger_net',
                                                              'tenant_id': 'admin'}})['network']
            pinger_subnet = self.api.create_subnet({'subnet': {'name': 'pinger_sub',
                                                               'network_id': pinger_net['id'],
                                                               'ip_version': 4, 'cidr': '192.168.88.0/24',
                                                               'tenant_id': 'admin'}})['subnet']

            self.LOG.debug('Created subnet for pinger pool: ' + str(pinger_subnet))

            lbaas_router = self.api.create_router({'router': {'name': 'lbaas_router',
                                                              'tenant_id': 'admin'}})['router']
            if1 = self.api.add_interface_router(lbaas_router['id'], {'subnet_id': member_subnet['id']})
            if2 = self.api.add_interface_router(lbaas_router['id'], {'subnet_id': lbaas_subnet['id']})
            if3 = self.api.add_interface_router(lbaas_router['id'], {'subnet_id': pinger_subnet['id']})
            self.LOG.debug('Created subnet router for LBaaS pool: ' + str(lbaas_router))
            self.LOG.debug('Created subnet interface for LBaaS pool on member net: ' + str(if1))
            self.LOG.debug('Created subnet interface for LBaaS pool on lbaas net: ' + str(if2))
            self.LOG.debug('Created subnet interface for a separate pinger net: ' + str(if3))
            router_ifs = [if1, if2, if3]

            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': member_net['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))
            ip1 = port1['fixed_ips'][0]['ip_address']
            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=member_subnet['gateway_ip'])
            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': member_net['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))
            ip2 = port2['fixed_ips'][0]['ip_address']
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], gw_ip=member_subnet['gateway_ip'])
            vm2.plugin_vm('eth0', port2['id'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))

            return TopoData(NetData(member_net, member_subnet),
                            NetData(lbaas_net, lbaas_subnet),
                            NetData(pinger_net, pinger_subnet),
                            RouterData(lbaas_router, router_ifs),
                            GuestData(port1, vm1, ip1),
                            GuestData(port2, vm2, ip2))

        except Exception as e:
            self.LOG.fatal('Error setting up topology: ' + str(e))
            raise e

    def clear_lbaas_topo(self, td):
        """
        :return:
        """
        if not td:
            return
        g1 = td.guest1
        g2 = td.guest2
        member = td.member
        lbaas = td.lbaas
        pinger = td.pinger
        lb_router = td.router

        if g1:
            self.cleanup_vms([(g1.vm, g1.port)])
        if g2:
            self.cleanup_vms([(g2.vm, g2.port)])
        if lb_router.router:
            self.api.update_router(lb_router.router['id'], {'router': {'routes': None}})
            for iface in lb_router.if_list:
                self.api.remove_interface_router(lb_router.router['id'], iface)
            self.api.delete_router(lb_router.router['id'])
        if lbaas.network:
            if lbaas.subnet:
                self.api.delete_subnet(lbaas.subnet['id'])
            if lbaas.network:
                self.api.delete_network(lbaas.network['id'])
        if pinger.network:
            if pinger.subnet:
                self.api.delete_subnet(pinger.subnet['id'])
            if pinger.network:
                self.api.delete_network(pinger.network['id'])
        if member.network:
            if member.subnet:
                self.api.delete_subnet(member.subnet['id'])
            if member.network:
                self.api.delete_network(member.network['id'])

    def send_packets_to_vip(self, host_list, pinger, vip):
        host_replies = {}
        """ :type: dict[str, int] """
        try:
            for g in host_list:
                g.vm.start_echo_server(ip=g.ip, echo_data=g.vm.vm_host.name)
                host_replies[g.vm.vm_host.name] = 0

            self.LOG.debug("Sending " + str(NUM_PACKETS_TO_SEND) +
                           " TCP count from LBaaS VM to VIP:" + str(vip))
            for i in range(0, NUM_PACKETS_TO_SEND):
                reply = pinger.vm.send_echo_request(dest_ip=str(vip), echo_request='ping').strip()
                self.LOG.debug('Got reply from echo-server: ' + reply)
                replying_vm = reply.split(':')[-1]
                if replying_vm == '':
                    self.fail("VIP didn't respond: " + vip)
                elif replying_vm not in host_replies:
                    self.fail('Received mismatched and unexpected reply: ' + reply + ' from VIP: ' + vip)
                host_replies[replying_vm] += 1

        finally:
            for g in host_list:
                g.vm.stop_echo_server()

        total_packet_count = sum(host_replies.values())

        self.LOG.debug("Got total of " + str(total_packet_count) + " packets")
        self.assertEqual(NUM_PACKETS_TO_SEND, total_packet_count)

        fail_list = []
        baseline_average = int(NUM_PACKETS_TO_SEND/len(host_list))
        acceptable_delta = int(NUM_PACKETS_TO_SEND/(2 * len(host_list)))
        for g in host_list:
            replies_on_vm = host_replies[g.vm.vm_host.name]
            self.LOG.debug("Got " + str(replies_on_vm) + " packets on VM with IP: " + g.ip)

            # round robin means the packets should be relatively evenly distributed
            # but it's not perfect, so allow about a 50% leeway for each host
            if replies_on_vm < baseline_average - acceptable_delta or \
               replies_on_vm > baseline_average + acceptable_delta:
                fail_list.append((g.vm.vm_host.name, replies_on_vm))

        if len(fail_list) > 0:
            self.fail('Packet counts outside of acceptable range (' +
                      str(baseline_average) + '+/-' + str(acceptable_delta) + '): ' +
                      ', '.join([g + ': ' + c for g, c in fail_list]))

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_round_robin(self):
        g1 = None
        g2 = None
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        td = None
        try:
            td = self.create_lbaas_network_topology()
            g1 = td.guest1
            g2 = td.guest2

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': td.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=td.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': td.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': td.lbaas.subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': 5080,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            member2 = self.api.create_member({'member': {'address': g2.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2))
            self.send_packets_to_vip([g1, g2], g_pinger, vip1['address'])

        finally:
            if pool1:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            self.clear_lbaas_topo(td)

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_round_robin_sender_on_host_subnet(self):
        g1 = None
        g2 = None
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        td = None
        try:
            td = self.create_lbaas_network_topology()
            g1 = td.guest1
            g2 = td.guest2

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': td.member.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=td.member.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': td.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': td.lbaas.subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': 5080,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            member2 = self.api.create_member({'member': {'address': g2.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2))

            self.send_packets_to_vip([g1, g2], g_pinger, vip1['address'])

        finally:
            if pool1:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            self.clear_lbaas_topo(td)

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_add_member(self):
        g1 = None
        g2 = None
        g3 = None
        g_pinger = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        td = None
        try:
            td = self.create_lbaas_network_topology()
            g1 = td.guest1
            g2 = td.guest2

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': td.pinger.network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, mac=port_pinger['mac_address'],
                                           gw_ip=td.pinger.subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            port3 = self.api.create_port({'port': {'name': 'port4',
                                                   'network_id': td.member.network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port3))

            ip3 = port3['fixed_ips'][0]['ip_address']
            vm3 = self.vtm.create_vm(ip=ip3, mac=port3['mac_address'],
                                     gw_ip=td.member.subnet['gateway_ip'])
            """ :type: Guest"""
            vm3.plugin_vm('eth0', port3['id'])
            g3 = GuestData(port3, vm3, ip3)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': td.lbaas.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': td.lbaas.subnet['id'],
                                                'protocol': 'TCP',
                                                'protocol_port': 5080,
                                                'pool_id': pool1['id'],
                                                'tenant_id': 'admin'}})['vip']
            self.LOG.debug('Created LBaaS VIP: ' + str(vip1))

            member1 = self.api.create_member({'member': {'address': g1.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            member2 = self.api.create_member({'member': {'address': g2.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']

            self.LOG.debug('Created member1 for LBaaS Pool: ' + str(member1))
            self.LOG.debug('Created member2 for LBaaS Pool: ' + str(member2))

            self.send_packets_to_vip([g1, g2], g_pinger, vip1['address'])

            member3 = self.api.create_member({'member': {'address': g3.ip,
                                                         'protocol_port': 5080,
                                                         'pool_id': pool1['id'],
                                                         'tenant_id': 'admin'}})['member']
            self.LOG.debug('Created member3 for LBaaS Pool: ' + str(member3))

            self.send_packets_to_vip([g1, g2, g3], g_pinger, vip1['address'])

        finally:
            if pool1:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            if g_pinger:
                self.cleanup_vms([(g_pinger.vm, g_pinger.port)])
            if g3:
                self.cleanup_vms([(g3.vm, g3.port)])
            self.clear_lbaas_topo(td)
