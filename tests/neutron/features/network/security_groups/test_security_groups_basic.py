# Copyright 2016 Midokura SARL
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


class TestSecurityGroupsBasic(NeutronTestCase):
    def test_security_group_basic_remote_group(self):
        cidr = "192.168.20.0/24"
        net = self.create_network('SG_BASIC')
        sub = self.create_subnet('SG_BASIC', net['id'], cidr)

        sg1 = self.create_security_group('SG_1')
        self.create_security_group_rule(sg1['id'], remote_group_id=sg1['id'])

        sg2 = self.create_security_group('SG_2')
        self.create_security_group_rule(sg2['id'], remote_group_id=sg1['id'])

        (porta, vma, ipa) = self.create_vm_server(
            "A", net['id'], sub['gateway_ip'], sgs=[sg1['id']])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", net['id'], sub['gateway_ip'], sgs=[sg1['id']])

        (portc, vmc, ipc) = self.create_vm_server(
            "C", net['id'], sub['gateway_ip'], sgs=[sg2['id']])

        self.assertTrue(vmb.verify_connection_to_host(vma))
        self.assertTrue(vma.verify_connection_to_host(vmb))
        self.assertFalse(vmc.verify_connection_to_host(vma, timeout=5))
        self.assertTrue(vma.verify_connection_to_host(vmc))

    def test_security_group_two_subnets(self):
        cidr = "192.168.20.0/24"
        net1 = self.create_network('SG_BASIC1')
        sub1 = self.create_subnet('SG_BASIC1', net1['id'], cidr)

        net2 = self.create_network('SG_BASIC2')
        sub2 = self.create_subnet('SG_BASIC2', net2['id'], cidr)

        self.create_router(
            'RTR1_2', priv_sub_ids=[net1['id'], net2['id']])

        sg1 = self.create_security_group('SG_1')
        self.create_security_group_rule(sg1['id'])

        sg2 = self.create_security_group('SG_2')
        self.create_security_group_rule(sg2['id'])

        (porta, vma, ipa) = self.create_vm_server(
            "A", net1['id'], sub1['gateway_ip'], sgs=[sg1['id']])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", net2['id'], sub2['gateway_ip'], sgs=[sg1['id']])

        (portc, vmc, ipc) = self.create_vm_server(
            "C", net1['id'], sub1['gateway_ip'], sgs=[sg2['id']])

        self.assertTrue(vmb.verify_connection_to_host(vma))
        self.assertTrue(vma.verify_connection_to_host(vmb))
        self.assertFalse(vmc.verify_connection_to_host(vma, timeout=5))
        self.assertFalse(vmc.verify_connection_to_host(vmb, timeout=5))

    def test_security_group_rules(self):
        cidr = "192.168.20.0/24"
        net1 = self.create_network('SG_BASIC1')
        sub1 = self.create_subnet('SG_BASIC1', net1['id'], cidr)

        net2 = self.create_network('SG_BASIC2')
        sub2 = self.create_subnet('SG_BASIC2', net2['id'], cidr)

        self.create_router(
            'RTR1_2', priv_sub_ids=[net1['id'], net2['id']])

        sg1 = self.create_security_group('SG_1')

        (porta, vma, ipa) = self.create_vm_server(
            "A", net1['id'], sub1['gateway_ip'], sgs=[sg1['id']])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", net2['id'], sub2['gateway_ip'], sgs=[sg1['id']])

        self.assertFalse(vmb.verify_connection_to_host(vma, timeout=5))
        self.assertFalse(vma.verify_connection_to_host(vmb, timeout=5))

        self.create_security_group_rule(sg1['id'])

        self.assertTrue(vmb.verify_connection_to_host(vma))
        self.assertTrue(vma.verify_connection_to_host(vmb))
