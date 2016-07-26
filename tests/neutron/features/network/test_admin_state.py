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


class TestAdminState(NeutronTestCase):
    def test_admin_state_port(self):
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.update_port(port1['id'], admin_state_up=False)
        self.assertFalse(vm1.verify_connection_to_host(vm2, timeout=5))
        self.update_port(port1['id'], admin_state_up=True)
        self.assertTrue(vm1.verify_connection_to_host(vm2))

    def test_admin_state_network(self):
        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.update_network(self.main_network['id'], admin_state_up=False)
        self.assertFalse(vm1.verify_connection_to_host(vm2, timeout=5))
        self.update_network(self.main_network['id'], admin_state_up=True)
        self.assertTrue(vm1.verify_connection_to_host(vm2))

    def test_admin_state_router(self):
        net1 = self.create_network(name='net1')
        sub1 = self.create_subnet(
            name='sub1', net_id=net1['id'], cidr='172.16.98.0/24')

        net2 = self.create_network(name='net2')
        sub2 = self.create_subnet(
            name='sub2', net_id=net2['id'], cidr='172.16.99.0/24')

        router2 = self.create_router(
            'router2', priv_sub_ids=[sub1['id'], sub2['id']])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=net1['id'],
            gw_ip=sub1['gateway_ip'])

        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=net2['id'],
            gw_ip=sub2['gateway_ip'])

        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.update_router(router2['id'], admin_state_up=False)
        self.assertFalse(vm1.verify_connection_to_host(vm2, timeout=5))
        self.update_router(router2['id'], admin_state_up=True)
        self.assertTrue(vm1.verify_connection_to_host(vm2))
