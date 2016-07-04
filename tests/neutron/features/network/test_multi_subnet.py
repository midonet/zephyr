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


class TestMultiSubnet(NeutronTestCase):
    def test_multiple_subnets_one_network(self):
        # Allowed address pair must have IP address
        net1def = {'network': {'name': 'net1', 'admin_state_up': True,
                               'tenant_id': 'admin'}}

        net1 = self.api.create_network(net1def)['network']
        self.LOG.debug('Created net1: ' + str(net1))

        subnet1def = {'subnet':
                      {'name': 'net1_sub1',
                       'network_id': net1['id'],
                       'ip_version': 4, 'cidr': '172.168.10.8/29',
                       'tenant_id': 'admin'}}
        subnet2def = {'subnet': {'name': 'net1_sub2',
                                 'network_id': net1['id'],
                                 'ip_version': 4, 'cidr': '172.168.1.8/29',
                                 'tenant_id': 'admin'}}

        subnet1 = self.api.create_subnet(subnet1def)['subnet']
        self.LOG.debug('Created subnet1: ' + str(subnet1))

        subnet2 = self.api.create_subnet(subnet2def)['subnet']
        self.LOG.debug('Created subnet2: ' + str(subnet2))

        (port1, vm1, ip1) = self.create_vm_server(
            'vm2', self.main_network['id'],
            subnet1['gateway_ip'])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', self.main_network['id'],
            subnet2['gateway_ip'])
        """ :type: Guest"""

        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))
        self.assertTrue(vm2.verify_connection_to_host(vm1, use_tcp=False))
