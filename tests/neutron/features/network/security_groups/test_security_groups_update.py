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

import time

from zephyr.tsm.neutron_test_case import NeutronTestCase


class TestRouterPeeringSecurityGroups(NeutronTestCase):

    def test_security_group_updates(self):
        cidr = "192.168.20.0/24"
        net = self.create_network('SEC_GROUP_UPDATE')
        sub = self.create_subnet('SEC_GROUP_UPDATE', net['id'], cidr)

        sg1 = self.create_security_group('SG_1')
        self.create_security_group_rule(sg1['id'], remote_group_id=sg1['id'])

        sg2 = self.create_security_group('SG_2')
        self.create_security_group_rule(sg2['id'],
                                        remote_ip_prefix='1.1.1.1/32')

        (porta, vma, ipa) = self.create_vm_server(
            "A", net['id'], sub['gateway_ip'], sgs=[sg1['id']])

        (portb, vmb, ipb) = self.create_vm_server(
            "B", net['id'], sub['gateway_ip'], sgs=[sg1['id']])

        (portc, vmc, ipc) = self.create_vm_server(
            "C", net['id'], sub['gateway_ip'], sgs=[sg1['id']])

        vmb.start_echo_server(ip_addr=ipb)
        self.check_ping_and_tcp(vma, ipb)

        vma.start_echo_server(ip_addr=ipa)
        self.check_ping_and_tcp(vmb, ipa)

        vmc.start_echo_server(ip_addr=ipc)
        self.check_ping_and_tcp(vma, ipc)

        self.api.update_port(porta['id'],
                             {'port': {'security_groups': [sg2['id']]}})

        # Allow time for topology changes to propagate to the agents
        time.sleep(1)
        self.check_ping_and_tcp(vmb, ipc)
        self.check_ping_and_tcp(vmc, ipb)

        self.assertFalse(vma.ping(ipb))
        self.assertFalse(vma.ping(ipc))
        self.assertFalse(vmb.ping(ipa))
        self.assertFalse(vmc.ping(ipa))

        self.api.update_port(porta['id'],
                             {'port': {'security_groups': [sg1['id']]}})

        # Allow time for topology changes to propagate to the agents
        time.sleep(1)
        self.check_ping_and_tcp(vmb, ipa)
