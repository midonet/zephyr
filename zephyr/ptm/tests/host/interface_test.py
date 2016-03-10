# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import unittest
from zephyr.common.cli import LinuxCLI
from zephyr.common.ip import IP
from zephyr.common.utils import run_unit_test
from zephyr.ptm.host.host import Host
from zephyr.ptm.host.interface import Interface


class InterfaceTest(unittest.TestCase):
    def test_use_active_iface(self):
        cli = LinuxCLI(log_cmd=True)
        h = Host('test', None, cli, lambda name: None, lambda name: None)
        i = Interface('testi', h, ip_addr=[IP.make_ip('192.168.0.2')])
        cli.cmd('ip l add dev testi type dummy')
        self.assertTrue(cli.grep_cmd('ip l | grep testi', 'state DOWN'))

        i.up()

        time.sleep(1)
        self.assertTrue(cli.grep_cmd('ip l | grep testi', 'UP'))

        i.down()

        self.assertFalse(cli.grep_cmd('ip l | grep testi', 'UP'))

        cli.cmd('ip l del testi')

    def tearDown(self):
        LinuxCLI().cmd('ip l del testi')


run_unit_test(InterfaceTest)
