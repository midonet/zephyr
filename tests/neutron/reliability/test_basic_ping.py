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

import operator

from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm import test_case


class TestBasicPing(NeutronTestCase):
    @test_case.require_hosts(['cmp1'])
    def test_neutron_api_ping_two_hosts_same_hv(self):
        (port1, vm1, ip1) = self.create_vm_server(
            name='vm1',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            name='vm2',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host=vm1.get_hypervisor_name())

        self.LOG.info('Verifying from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.LOG.info('Verifying from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1))

    @test_case.require_hosts(['cmp1', 'cmp2'])
    def test_neutron_api_ping_two_hosts_diff_hv(self):
        (port1, vm1, ip1) = self.create_vm_server(
            name='vm1',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            name='vm2',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host='!' + vm1.get_hypervisor_name())

        self.LOG.info('Verifying from VM1 to VM2')
        self.assertTrue(vm1.verify_connection_to_host(vm2))
        self.LOG.info('Verifying from VM2 to VM1')
        self.assertTrue(vm2.verify_connection_to_host(vm1))
