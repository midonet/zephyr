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

from TSM.NeutronTestCase import GuestData
from TSM.NeutronTestCase import NetData
from TSM.NeutronTestCase import NeutronTestCase
from TSM.NeutronTestCase import require_extension
from TSM.NeutronTestCase import RouterData
from collections import namedtuple
from common.EchoServer import DEFAULT_ECHO_PORT

from tests.neutron.features.lbaas.lbaas_test_utils import *


class TestLBaaSSessionPersistence(NeutronTestCase):

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_session_persistence(self):
        g1 = None
        g2 = None
        pinger_data = []
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
                                                'session_persistence': {'type': 'SOURCE_IP'},
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

            g1.vm.start_echo_server(ip=g1.ip, echo_data=g1.vm.vm_host.name)
            g2.vm.start_echo_server(ip=g2.ip, echo_data=g2.vm.vm_host.name)

            for i in range(0, 20):
                pport = self.api.create_port({'port': {'name': 'port_p' + str(i),
                                                       'network_id': lbn_data.pinger.network['id'],
                                                       'admin_state_up': True,
                                                       'tenant_id': 'admin'}})['port']
                pip = pport['fixed_ips'][0]['ip_address']
                pvm = self.vtm.create_vm(ip=pip, mac=pport['mac_address'], gw_ip=lbn_data.pinger.subnet['gateway_ip'])
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
            clear_lbaas_data(self, lbn_data)
