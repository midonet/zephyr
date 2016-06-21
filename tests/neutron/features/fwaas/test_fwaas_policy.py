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

from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.vtm import fwaas_fixture


class TestFWaaSPolicy(NeutronTestCase):
    def setUp(self):
        fwaas_fixture.FWaaSFixture().setup()

    @require_extension("fwaas")
    def test_basic_policy(self):
        near_net = self.create_network('near_net')
        near_sub = self.create_subnet(
            'near_sub',
            net_id=near_net['id'],
            cidr='192.179.100.0/24')

        far_net = self.create_network('far_net')
        far_sub = self.create_subnet(
            'far_sub',
            net_id=far_net['id'],
            cidr='192.179.200.0/24')

        near_far_router = self.create_router(
            'near_far_router',
            priv_sub_ids=[far_sub['id'], near_sub['id']])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1',
            net_id=near_net['id'],
            gw_ip=near_sub['gateway_ip'],
            port_security_enabled=False)
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2',
            net_id=far_net['id'],
            gw_ip=far_sub['gateway_ip'],
            port_security_enabled=False)

        fwp = self.create_firewall_policy('POLICY')
        self.create_firewall(fwp['id'],
                             router_ids=[near_far_router['id']])

        fwr = self.create_firewall_rule(action='allow', protocol='tcp',
                                        dest_port=7777)
        self.insert_firewall_rule(fw_policy_id=fwp['id'],
                                  fw_rule_id=fwr['id'])

        vm2.start_echo_server(ip=ip2, port=7777, echo_data='pong')
        reply = vm1.send_echo_request(dest_ip=ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        vm2.start_echo_server(ip=ip2, port=8888, echo_data='pong')
        reply = vm1.send_echo_request(dest_ip=ip2, dest_port=8888)
        self.assertEqual('', reply)
