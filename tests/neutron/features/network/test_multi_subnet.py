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

from common.PCAPRules import *
from common.PCAPPacket import *
from TSM.NeutronTestCase import NeutronTestCase
from VTM.Guest import Guest

from collections import namedtuple
from neutronclient.common.exceptions import *

import unittest


class TestMultiSubnet(NeutronTestCase):
    def test_multiple_subnets_one_network(self):
        # Allowed address pair must have IP address
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:

            net1def = {'network': {'name': 'net1', 'admin_state_up': True,
                                   'tenant_id': 'admin'}}

            net1 = self.api.create_network(net1def)['network']
            self.LOG.debug('Created net1: ' + str(net1))

            subnet1def = {'subnet': {'name': 'net1_sub1',
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

            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=subnet1['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], gw_ip=subnet2['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])
