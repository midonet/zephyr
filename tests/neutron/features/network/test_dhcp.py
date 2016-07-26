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
from zephyr.tsm.test_case import require_topology_feature


class TestDHCP(NeutronTestCase):
    @require_topology_feature('dhcp_on_vm')
    def test_dhcp_disable(self):
        net1 = self.create_network(name='net1')
        sub1 = self.create_subnet(
            name='sub1', net_id=net1['id'], cidr='172.16.98.0/24')

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=net1['id'],
            gw_ip=sub1['gateway_ip'])

        self.assertIsNotNone(vm1.get_ip('eth0'))
        self.update_subnet(sub1['id'], enable_dhcp=False)

        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=net1['id'],
            gw_ip=sub1['gateway_ip'])

        self.assertIsNone(vm2.get_ip('eth0'))

    @require_topology_feature('dhcp_on_vm')
    def test_dhcp_lease(self):
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        self.assertIsNotNone(vm1.get_ip('eth0'))
        # TODO(micucci) Check DNS settings and routes
