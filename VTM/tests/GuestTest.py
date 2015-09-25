__author__ = 'micucci'

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


from common.IP import IP
from common.CLI import LinuxCLI

from PTM.VMHost import VMHost
from PTM.HypervisorHost import HypervisorHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from VTM.Guest import Guest
from VTM.VirtualTopologyManager import VirtualTopologyManager

import logging
import datetime
import os
from common.LogManager import LogManager


class MockClient(object):
    def __init__(self, *args, **kwargs):
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
    lm=LogManager('test-logs')
    ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

    @classmethod
    def setUpClass(cls):
        cls.ptm.configure(os.path.dirname(os.path.abspath(__file__)) + '/test-basic-config.json')
        cls.ptm.startup()

    def test_host_plugin_vm(self):
        vtm = VirtualTopologyManager(client_api_impl=MockClient,
                                     physical_topology_manager=self.ptm)

        hv = self.ptm.hypervisors['cmp1']
        """ :type hv: HypervisorHost """

        vm = hv.create_vm('vm1')
        try:
            vm.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])

            # Normally we get this from network, but just go with a mocked up port for this test
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
        vtm = VirtualTopologyManager(client_api_impl=MockClient,
                                     physical_topology_manager=self.ptm)

        hv1 = self.ptm.hosts_by_name['cmp1']
        """ :type hv1: HypervisorHost """
        hv2 = self.ptm.hosts_by_name['cmp2']
        """ :type hv2: HypervisorHost """

        vm1 = hv1.create_vm('vm1')
        vm2 = hv2.create_vm('vm2')

        try:
            vm1.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])
            vm2.create_interface('eth0', ip_list=[IP("10.55.55.55", "8")])

            # Normally we get this from network, but just go with a mocked up port for this test
            port1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            port2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

            virtual_host1 = Guest(vm1)
            virtual_host1.plugin_vm('eth0', port1)

            virtual_host2 = Guest(vm2)
            virtual_host2.plugin_vm('eth0', port2)

            # No virtual bridge between VMs means they should NOT talk to each other yet.
            self.assertFalse(virtual_host1.ping('eth0', '10.55.55.55'))

            virtual_host1.unplug_vm(port1)
            virtual_host2.unplug_vm(port2)

        finally:
            vm1.net_down()
            vm2.net_down()
            vm1.shutdown()
            vm2.shutdown()
            vm1.remove()
            vm2.remove()

    @classmethod
    def tearDownClass(cls):
        cls.ptm.shutdown()
        LinuxCLI().cmd('ip netns del vm1')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(GuestTest)
