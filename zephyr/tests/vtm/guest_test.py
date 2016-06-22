
import unittest


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


import os

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class GuestTest(unittest.TestCase):
    lm = None
    vtm = None

    @classmethod
    def setUpClass(cls):
        cls.lm = LogManager('test-logs')
        cls.vtm = VirtualTopologyManager(log_manager=cls.lm)
        cls.vtm.configure_logging(debug=True)
        cls.vtm.read_underlay_config()

    def test_host_plugin_vm(self):
        vm = self.vtm.create_vm(
            name='vm1', ip_addr="10.3.3.3")
        try:
            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port = "fe6707e3-9c99-4529-b059-aa669d1463bb"

            vm.plugin_vm('eth0', port)

            self.assertTrue(port in vm.open_ports_by_id)

            vm.unplug_vm(port)

            self.assertFalse(port in vm.open_ports_by_id)
        finally:
            vm.terminate()

    def test_echo_server_tcp(self):
        vm1 = self.vtm.create_vm(
            name='vm1', ip_addr="10.3.3.3")

        try:
            vm1.start_echo_server(echo_data='test')
            ret = vm1.send_echo_request(echo_request='ping')
            self.assertEqual('ping:test', ret)

        finally:
            vm1.stop_echo_server()
            vm1.terminate()

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip netns del vm1')

run_unit_test(GuestTest)
