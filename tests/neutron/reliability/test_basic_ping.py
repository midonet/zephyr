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
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host='cmp1')
        (port2, vm2, ip2) = self.create_vm_server(
            name='vm2',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host='cmp1')

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))

    @test_case.require_hosts(['cmp1', 'cmp2'])
    def test_neutron_api_ping_two_hosts_diff_hv(self):
        (port1, vm1, ip1) = self.create_vm_server(
            name='vm1',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host='cmp1')
        (port2, vm2, ip2) = self.create_vm_server(
            name='vm2',
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            hv_host='cmp2')

        self.LOG.info('Pinging from VM1 to VM2')
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

        self.LOG.info('Pinging from VM2 to VM1')
        self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))
