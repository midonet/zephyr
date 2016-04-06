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

import datetime
import time
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common.ip import IP
from zephyr.common.utils import run_unit_test
from zephyr.ptm.host.bridge import Bridge
from zephyr.ptm.host.host import Host
from zephyr.ptm.host.virtual_interface import VirtualInterface


class BridgeTest(unittest.TestCase):
    def test_create(self):
        cli = LinuxCLI()
        h = Host('test', None, cli, lambda name: None, lambda name: None)
        i = VirtualInterface('testi', host=h,
                             ip_addr=[IP.make_ip('192.168.0.2')])

        i.create()
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=5)

        while not cli.grep_cmd('ip l', 'testi'):
            if datetime.datetime.now() > deadline:
                self.fail("Interface on bridge failed to be added "
                          "within timeout")
            time.sleep(1)

        b = Bridge('test-bridge', h, ip_addr=[IP.make_ip('192.168.0.240')],
                   options=['stp'])

        b.create()
        time.sleep(1)

        # Check bridge is present
        self.assertTrue(h.cli.grep_cmd(
            'brctl show | grep test-bridge | cut -f 1', 'test-bridge'))
        # Check STP
        self.assertTrue(h.cli.grep_cmd(
            'brctl show | grep test-bridge | cut -f 4', 'yes'))

        b.link_interface(i)
        time.sleep(1)
        # Check interface has bridge set as link
        self.assertTrue(h.cli.grep_cmd('ip l | grep testi', 'test-bridge'))

        b.remove()
        i.remove()

        self.assertFalse(cli.grep_cmd('ip l', 'testi'))
        self.assertFalse(cli.grep_cmd('brctl show', 'test-bridge'))

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip l del test-bridge')
        LinuxCLI().cmd('brctl delbr test-bridge')
        LinuxCLI().cmd('ip l del testi')


run_unit_test(BridgeTest)
