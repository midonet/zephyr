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


class TestRouterPeeringSecurityGroups(NeutronTestCase):

    def test_security_group_basic_remote_group(self):
        try:
            self.security_group_remote_group()
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    def security_group_remote_group(self):
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

        vmb.start_echo_server(ip_addr=ipb)
        self.verify_connectivity(vma, ipb)

        vma.start_echo_server(ip_addr=ipa)
        self.verify_connectivity(vmb, ipa)

        self.assertFalse(vmc.ping(ipa))

        vmc.start_echo_server(ip_addr=ipc)
        self.verify_connectivity(vma, ipc)
