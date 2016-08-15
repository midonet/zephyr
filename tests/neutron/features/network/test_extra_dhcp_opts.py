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

from zephyr.common.cli import LinuxCLI
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.test_case import require_topology_feature


class TestExtraDhcpOpts(NeutronTestCase):

    def test_basic_extra_opt_router_ip(self):
        cidr = "192.168.10.0/24"
        router_ip = "192.168.10.10"
        net = self.create_network('NET')
        sub = self.create_subnet('NET', net['id'], cidr)

        (port, vm, ip) = self.create_vm_server(
            "A", net['id'], sub['gateway_ip'], router_ip=router_ip)
        cmd = "ip netns exec A ip route | head -1 | cut -d' ' -f3"
        default_gw = LinuxCLI().cmd(cmd).stdout.rstrip()
        self.assertEqual(default_gw, router_ip)
