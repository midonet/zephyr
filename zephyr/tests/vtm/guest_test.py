
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
from zephyr.common.ip import IP
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.common import zephyr_constants as z_con
from zephyr.vtm.guest import Guest
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class GuestTest(unittest.TestCase):
    lm = None
    ptm = None

    @classmethod
    def setUpClass(cls):
        cls.lm = LogManager('test-logs')

    def test_host_plugin_vm(self):
        vtm = VirtualTopologyManager()
        vtm.read_underlay_config()

        vm = vtm.create_vm(name='vm1', ip_addr="10.3.3.3", hv_host='cmp1')
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

    def test_host_cross_vm_communication(self):
        vtm = VirtualTopologyManager()
        vtm.configure_logging(debug=True)
        vtm.read_underlay_config()

        vm1 = vtm.create_vm(name='vm1', ip_addr="10.3.3.3", hv_host='cmp1')
        vm2 = vtm.create_vm(name='vm2', ip_addr="10.55.55.55", hv_host='cmp2')

        try:
            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            port2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

            vm1.plugin_vm('eth0', port1)
            vm2.plugin_vm('eth0', port2)

            # No virtual bridge between VMs means they should NOT talk
            # to each other yet.
            self.assertFalse(vm1.ping('10.55.55.55', 'eth0'))

            vm1.unplug_vm(port1)
            vm2.unplug_vm(port2)

        finally:
            vm1.terminate()
            vm2.terminate()

    def test_echo_server_tcp(self):
        vtm = VirtualTopologyManager()
        vtm.configure_logging(debug=True)
        vtm.read_underlay_config()

        vm1 = vtm.create_vm(name='vm1', ip_addr="10.3.3.3", hv_host='cmp1')

        try:
            vm1.vm_underlay.create_interface(
                'eth1', ip_list=[IP("10.3.3.4", "8")])

            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

            vm1.plugin_vm('eth0', port1)

            vm1.start_echo_server(echo_data='test')
            ret = vm1.send_echo_request(echo_request='ping')
            self.assertEqual('ping:test', ret)
            vm1.stop_echo_server()

            vm1.unplug_vm(port1)

        finally:
            vm1.stop_echo_server()
            vm1.terminate()

    # TODO(micucci): Fix UDP
    # def test_echo_server_udp(self):
    #     vtm = VirtualTopologyManager(physical_topology_manager=self.ptm)
    #
    #     hv1 = self.ptm.hypervisors['cmp1'][0]
    #     """ :type hv1: Midolman """
    #
    #     vm1 = hv1.create_vm('vm1')
    #     virtual_host1 = Guest(vm1)
    #
    #     try:
    #         vm1.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])
    #
    #         # Normally we get this from network, but just go with a mocked
    #         # up port for this test
    #         port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    #
    #         virtual_host1.plugin_vm('eth0', port1)
    #
    #         virtual_host1.start_echo_server(echo_data='test', protocol='udp')
    #         ret = virtual_host1.send_echo_request(echo_request='ping',
    #                                               protocol='udp')
    #         self.assertEqual('ping:test', ret)
    #         virtual_host1.stop_echo_server()
    #
    #         virtual_host1.unplug_vm(port1)
    #
    #     finally:
    #         virtual_host1.stop_echo_server()
    #         vm1.net_down()
    #         vm1.shutdown()
    #         vm1.remove()

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip netns del vm1')

run_unit_test(GuestTest)
