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

NUM_PACKETS_TO_SEND = 50


class TestLBaaSSessionPersistence(NeutronTestCase):
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

            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip=ip1))

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

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_session_persistence(self):
        g1 = None
        g2 = None
        pinger_data = []
        lb_net = None
        lb_router = None
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        try:
            (g1, g2, lb_net, lb_router) = self.create_lbaas_network_topology()

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
                                                'session_persistence': {'type': 'SOURCE_IP'},
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

            g1.vm.start_echo_server(ip=g1.ip, echo_data=g1.vm.vm_host.name)
            g2.vm.start_echo_server(ip=g2.ip, echo_data=g2.vm.vm_host.name)

            for i in range(0, 20):
                pport = self.api.create_port({'port': {'name': 'port_p' + str(i),
                                                       'network_id': self.pinger_net['id'],
                                                       'admin_state_up': True,
                                                       'tenant_id': 'admin'}})['port']
                pip = pport['fixed_ips'][0]['ip_address']
                pvm = self.vtm.create_vm(ip=pip, gw_ip=self.pinger_subnet['gateway_ip'])
                pvm.plugin_vm('eth0', pport['id'], pport['mac_address'])

                resp = pvm.send_echo_request(dest_ip=str(vip1['address']), echo_request='ping')

                if resp == "ping:" or resp == "":
                    self.fail('No response from VIP: ' + vip1['address'])
                pinger_data.append((pport, pvm, resp.split(':')[-1]))

            # 100 times, go through each VM and echo to VIP and make sure the same backend
            # member answers the echo as the first time
            for i in range(0, 100):
                for port, ping_vm, responding_vm in pinger_data:
                    resp = ping_vm.send_echo_request(dest_ip=str(vip1['address']), echo_request='ping')
                    self.assertEqual(responding_vm, resp.split(':')[-1])

        finally:
            for port, ping_vm, responding_vm in pinger_data:
                self.cleanup_vms([(ping_vm, port)])

            if pool1 is not None:
                self.api.delete_vip(vip1['id'])
                self.api.delete_member(member1['id'])
                self.api.delete_member(member2['id'])
                self.api.delete_pool(pool1['id'])
            self.clear_lbaas_topo(lb_net, lb_router)
            self.cleanup_vms([(g1.vm, g1.port), (g2.vm, g2.port)])
