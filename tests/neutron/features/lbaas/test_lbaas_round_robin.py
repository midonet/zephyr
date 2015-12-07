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
from tests.scenarios.Scenario_Basic2Compute import Scenario_Basic2Compute
from common.CLI import NetNSCLI, CommandStatus
import unittest

import time

NUM_PACKETS_TO_SEND = 50


class TestLBaaSRoundRobin(NeutronTestCase):
    @staticmethod
    def supported_scenarios():
        return {Scenario_Basic2Compute}

    def create_lbaas_network_topology(self):
        try:
            self.lbaas_net = self.api.create_network({'network': {'name': 'lbaas_net',
                                                             'tenant_id': 'admin'}})['network']
            self.lbaas_subnet = self.api.create_subnet({'subnet': {'name': 'lbaas_sub',
                                                              'network_id': self.lbaas_net['id'],
                                                              'ip_version': 4, 'cidr': '192.168.55.0/24',
                                                              'tenant_id': 'admin'}})['subnet']

            self.LOG.debug('Created subnet for LBaaS pool: ' + str(self.lbaas_subnet))

            self.pinger_net = self.api.create_network({'network': {'name': 'pinger_net',
                                                              'tenant_id': 'admin'}})['network']
            self.pinger_subnet = self.api.create_subnet({'subnet': {'name': 'pinger_sub',
                                                               'network_id': self.pinger_net['id'],
                                                               'ip_version': 4, 'cidr': '192.168.88.0/24',
                                                               'tenant_id': 'admin'}})['subnet']

            self.LOG.debug('Created subnet for pinger pool: ' + str(self.pinger_subnet))

            self.lbaas_router = self.api.create_router({'router': {'name': 'lbaas_router',
                                                              'tenant_id': 'admin'}})['router']
            if1 = self.api.add_interface_router(self.lbaas_router['id'], {'subnet_id': self.lbaas_subnet['id']})
            if2 = self.api.add_interface_router(self.lbaas_router['id'], {'subnet_id': self.main_subnet['id']})
            if3 = self.api.add_interface_router(self.lbaas_router['id'], {'subnet_id': self.pinger_subnet['id']})

            self.LOG.debug('Created subnet router for LBaaS pool: ' + str(self.lbaas_router))
            self.LOG.debug('Created subnet interface for LBaaS pool on main net: ' + str(if1))
            self.LOG.debug('Created subnet interface for LBaaS pool on lbaas net: ' + str(if2))
            self.LOG.debug('Created subnet interface for a separate pinger net: ' + str(if3))

            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))
            ip1 = port1['fixed_ips'][0]['ip_address']
            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))
            ip2 = port2['fixed_ips'][0]['ip_address']
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))

            return (GuestData(port1, vm1, ip1),
                    GuestData(port2, vm2, ip2),
                    NetData(self.lbaas_net, self.lbaas_subnet),
                    RouterData(self.lbaas_router, [if1, if2, if3]))

        except Exception as e:
            self.LOG.fatal('Error setting up topology: ' + str(e))
            raise e

    def clear_lbaas_topo(self, net_data, router):
        """
        :type net_data: NetData
        :type router: RouterData
        :return:
        """
        if router is not None:
            if router.router is not None:
                self.api.update_router(router.router['id'], {'router': {'routes': None}})
                if router.if_list is not None:
                    for iface in router.if_list:
                        self.api.remove_interface_router(router.router['id'], iface)
                self.api.delete_router(router.router['id'])
        if net_data is not None:
            if net_data.subnet is not None:
                self.api.delete_subnet(net_data.subnet['id'])
            if net_data.network is not None:
                self.api.delete_network(net_data.network['id'])

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
                      str(baseline_average) +'+/-' + str(acceptable_delta) + '): ' +
                      ', '.join([g + ': ' + c for g, c in fail_list]))

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_round_robin(self):
        g1 = None
        g2 = None
        g_pinger = None
        lb_net = None
        lb_router = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        try:
            (g1, g2, lb_net, lb_router) = self.create_lbaas_network_topology()

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': self.pinger_net['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, gw_ip=self.pinger_subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'], port_pinger['mac_address'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lb_net.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lb_net.subnet['id'],
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
            if pool1 is not None:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            self.clear_lbaas_topo(lb_net, lb_router)
            self.cleanup_vms([(g1.vm, g1.port), (g2.vm, g2.port), (g_pinger.vm, g_pinger.port)])

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_round_robin_sender_on_host_subnet(self):
        g1 = None
        g2 = None
        g_pinger = None
        lb_net = None
        lb_router = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        try:
            (g1, g2, lb_net, lb_router) = self.create_lbaas_network_topology()

            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': self.main_network['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, gw_ip=self.main_subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'], port_pinger['mac_address'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lb_net.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lb_net.subnet['id'],
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
            if pool1 is not None:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            self.clear_lbaas_topo(lb_net, lb_router)
            self.cleanup_vms([(g1.vm, g1.port), (g2.vm, g2.port), (g_pinger.vm, g_pinger.port)])

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_add_member(self):
        g1 = None
        g2 = None
        g3 = None
        g_pinger = None
        lb_net = None
        lb_router = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        try:
            (g1, g2, lb_net, lb_router) = self.create_lbaas_network_topology()
            port_pinger = self.api.create_port({'port': {'name': 'port3',
                                                         'network_id': self.pinger_net['id'],
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for lbaas pinger: ' + str(port_pinger))

            ip_pinger = port_pinger['fixed_ips'][0]['ip_address']
            vm_pinger = self.vtm.create_vm(ip=ip_pinger, gw_ip=self.pinger_subnet['gateway_ip'])
            vm_pinger.plugin_vm('eth0', port_pinger['id'], port_pinger['mac_address'])
            g_pinger = GuestData(port_pinger, vm_pinger, ip_pinger)

            port3 = self.api.create_port({'port': {'name': 'port4',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port3))

            ip3 = port3['fixed_ips'][0]['ip_address']
            vm3 = self.vtm.create_vm(ip=ip3, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm3.plugin_vm('eth0', port3['id'], port3['mac_address'])
            g3 = GuestData(port3, vm3, ip3)

            pool1 = self.api.create_pool({'pool': {'name': 'pool1',
                                                   'protocol': 'TCP',
                                                   'subnet_id': lb_net.subnet['id'],
                                                   'lb_method': 'ROUND_ROBIN',
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['pool']
            self.LOG.debug('Created LBaaS Pool: ' + str(pool1))

            vip1 = self.api.create_vip({'vip': {'name': 'pool1-vip1',
                                                'subnet_id': lb_net.subnet['id'],
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
            if pool1 is not None:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            self.clear_lbaas_topo(lb_net, lb_router)
            self.cleanup_vms([(g1.vm, g1.port), (g2.vm, g2.port), (g_pinger.vm, g_pinger.port),
                              (g3.vm, g3.port)])
