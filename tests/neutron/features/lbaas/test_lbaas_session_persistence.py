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

from tests.neutron.features.lbaas.lbaas_test_utils import DEFAULT_POOL_PORT
from tests.neutron.features.lbaas.lbaas_test_utils import LBaaSTestCase
from zephyr.tsm.neutron_test_case import require_extension


class TestLBaaSSessionPersistence(LBaaSTestCase):

    @require_extension('lbaas')
    def test_lbaas_basic_internal_vip_session_persistence(self):
        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            vipa = self.create_vip(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'],
                protocol_port=DEFAULT_POOL_PORT,
                name='poola-vip1',
                pool_id=poola['id'])
            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            g1.vm.start_echo_server(ip=g1.ip, echo_data=g1.vm.vm_host.name)
            g2.vm.start_echo_server(ip=g2.ip, echo_data=g2.vm.vm_host.name)

            pinger_data = []
            for i in range(0, 20):
                g_pinger = self.create_pinger_vm(
                    name='pinger_' + str(i))

                resp = g_pinger.vm.send_echo_request(
                    dest_ip=str(vipa['address']),
                    echo_request='ping')

                if resp == "ping:" or resp == "":
                    self.fail('No response from VIP: ' + vipa['address'])
                pinger_data.append((g_pinger.vm, resp.split(':')[-1]))

            fails = []
            # 20 more times, go through each VM and echo to VIP and make
            # sure the same backend member answers the echo as the first time
            for i in range(0, 20):
                for ping_vm, responding_vm in pinger_data:
                    resp = ping_vm.send_echo_request(
                        dest_ip=str(vipa['address']),
                        echo_request='ping')
                    if resp.split(':')[-1] != responding_vm:
                        fails.append(resp.split(':')[-1] + ' != ' +
                                     responding_vm)
            if len(fails) > 0:
                self.fail('\n'.join(fails))

        finally:
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
