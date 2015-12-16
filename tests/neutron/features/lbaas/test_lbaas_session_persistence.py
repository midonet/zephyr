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


class TestLBaaSSessionPersistence(NeutronTestCase):
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
        member = td.member
        lbaas = td.lbaas
        pinger = td.pinger
        lb_router = td.router
        g1 = td.guest1
        g2 = td.guest2

        if g1:
            self.cleanup_vms([(g1.vm, g1.port)])
        if g2:
            self.cleanup_vms([(g2.vm, g2.port)])
        if lb_router.router is not None:
            self.api.update_router(lb_router.router['id'], {'router': {'routes': None}})
            for iface in lb_router.if_list:
                self.api.remove_interface_router(lb_router.router['id'], iface)
            self.api.delete_router(lb_router.router['id'])
        if lbaas.network is not None:
            if lbaas.subnet is not None:
                self.api.delete_subnet(lbaas.subnet['id'])
            if lbaas.network is not None:
                self.api.delete_network(lbaas.network['id'])
        if pinger.network is not None:
            if pinger.subnet is not None:
                self.api.delete_subnet(pinger.subnet['id'])
            if pinger.network is not None:
                self.api.delete_network(pinger.network['id'])
        if member.network is not None:
            if member.subnet is not None:
                self.api.delete_subnet(member.subnet['id'])
            if member.network is not None:
                self.api.delete_network(member.network['id'])

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_session_persistence(self):
        g1 = None
        g2 = None
        pinger_data = []
        pool1 = None
        vip1 = None
        member1 = None
        member2 = None
        td = None
        try:
            td = self.create_lbaas_network_topology()
            g1 = td.guest1
            g2 = td.guest2
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
                                                       'network_id': td.pinger.network['id'],
                                                       'admin_state_up': True,
                                                       'tenant_id': 'admin'}})['port']
                pip = pport['fixed_ips'][0]['ip_address']
                pvm = self.vtm.create_vm(ip=pip, mac=pport['mac_address'], gw_ip=td.pinger.subnet['gateway_ip'])
                pvm.plugin_vm('eth0', pport['id'])

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
            self.clear_lbaas_topo(td)
