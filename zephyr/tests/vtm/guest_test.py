
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
from zephyr.vtm.guest import Guest
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class MockClient(object):
    def __init__(self, **kwargs):
        super(MockClient, self).__init__()
        self.subnet = {}
        self.options = {}
        if kwargs is not None:
            for k, v in kwargs.iteritems():
                self.options[k] = v
        pass

    def list_ports(self):
        pass

    def list_networks(self):
        pass

    def delete_port(self, port):
        pass

    def delete_network(self, network):
        pass

    def set_subnet(self, subnet):
        self.subnet = subnet

    def show_subnet(self):
        return self.subnet

    def get_option(self, key):
        if key in self.options:
            return self.options[key]
        return None


class GuestTest(unittest.TestCase):
    lm = None
    ptm = None

    @classmethod
    def setUpClass(cls):
        cls.lm = LogManager('test-logs')
        cls.ptm = PhysicalTopologyManager(
            root_dir=ROOT_DIR,
            log_manager=cls.lm)
        cls.ptm.configure_logging(debug=True)
        cls.ptm.configure(
            config_file='test-basic-config.json',
            config_dir=os.path.dirname(os.path.abspath(__file__)))
        cls.ptm.startup()

    def test_host_plugin_vm(self):
        VirtualTopologyManager(client_api_impl=MockClient,
                               physical_topology_manager=self.ptm)

        hv = self.ptm.hypervisors['cmp1'][0]
        """ :type hv: Midolman """

        vm = hv.create_vm('vm1')
        try:
            vm.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])

            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port = "fe6707e3-9c99-4529-b059-aa669d1463bb"

            virtual_host = Guest(vm)
            virtual_host.plugin_vm('eth0', port)

            self.assertTrue(port in virtual_host.open_ports_by_id)

            virtual_host.unplug_vm(port)

            self.assertFalse(port in virtual_host.open_ports_by_id)
        finally:
            vm.net_down()
            vm.shutdown()
            vm.remove()

    def test_host_cross_vm_communication(self):
        VirtualTopologyManager(client_api_impl=MockClient,
                               physical_topology_manager=self.ptm)

        hv1 = self.ptm.hypervisors['cmp1'][0]
        """ :type hv1: Midolman """
        hv2 = self.ptm.hypervisors['cmp2'][0]
        """ :type hv2: Midolman """

        vm1 = hv1.create_vm('vm1')
        vm2 = hv2.create_vm('vm2')

        try:
            vm1.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])
            vm2.create_interface('eth0', ip_list=[IP("10.55.55.55", "8")])

            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            port2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

            virtual_host1 = Guest(vm1)
            virtual_host1.plugin_vm('eth0', port1)

            virtual_host2 = Guest(vm2)
            virtual_host2.plugin_vm('eth0', port2)

            # No virtual bridge between VMs means they should NOT talk
            # to each other yet.
            self.assertFalse(virtual_host1.ping('10.55.55.55', 'eth0'))

            virtual_host1.unplug_vm(port1)
            virtual_host2.unplug_vm(port2)

        finally:
            vm1.net_down()
            vm2.net_down()
            vm1.shutdown()
            vm2.shutdown()
            vm1.remove()
            vm2.remove()

    def test_echo_server_tcp(self):
        VirtualTopologyManager(client_api_impl=MockClient,
                               physical_topology_manager=self.ptm)

        hv1 = self.ptm.hypervisors['cmp1'][0]
        """ :type hv1: Midolman """

        vm1 = hv1.create_vm('vm1')
        virtual_host1 = Guest(vm1)

        try:
            vm1.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])

            # Normally we get this from network, but just go with a mocked
            # up port for this test
            port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

            virtual_host1.plugin_vm('eth0', port1)

            virtual_host1.start_echo_server(echo_data='test')
            ret = virtual_host1.send_echo_request(echo_request='ping')
            self.assertEqual('ping:test', ret)
            virtual_host1.stop_echo_server()

            virtual_host1.unplug_vm(port1)

        finally:
            virtual_host1.stop_echo_server()
            vm1.net_down()
            vm1.shutdown()
            vm1.remove()

    # TODO(micucci): Fix UDP
    # def test_echo_server_udp(self):
    #     vtm = VirtualTopologyManager(client_api_impl=MockClient,
    #                                  physical_topology_manager=self.ptm)
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
        cls.ptm.shutdown()
        LinuxCLI().cmd('ip netns del vm1')

run_unit_test(GuestTest)
