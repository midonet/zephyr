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
from PTM.ComputeHost import ComputeHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from VTM.Guest import Guest
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.tests.VirtualTopologyManagerTest import MockClient
from VTM.Network import Network
from VTM.Port import Port

import logging
import datetime

class GuestTest(unittest.TestCase):
    def setUp(self):
        self.ptm = PhysicalTopologyManager(root_dir='../..', log_root_dir='./tmp/logs')
        self.ptm.configure('test-basic-config.json')
        self.ptm.startup()

    def donttest_host_plugin_vm(self):
        vtm = VirtualTopologyManager(client_api_impl=MockClient,
                                     physical_topology_manager=self.ptm)

        hv = self.ptm.hosts_by_name['cmp1']
        """ :type hv: ComputeHost """

        vm = hv.create_vm('vm1')
        vm.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])

        # Normally we get this from network, but just go with a mocked up port for this test
        port = Port("fe6707e3-9c99-4529-b059-aa669d1463bb")

        virtual_host = Guest(vm)
        virtual_host.plugin_vm('eth0', port)

        self.assertEquals(virtual_host.open_ports_by_id[port.id].id, port.id)

        virtual_host.unplug_vm(port)

        self.assertFalse(port.id in virtual_host.open_ports_by_id)

    def test_host_cross_vm_communication(self):
        vtm = VirtualTopologyManager(client_api_impl=MockClient,
                                     physical_topology_manager=self.ptm)

        hv1 = self.ptm.hosts_by_name['cmp1']
        """ :type hv1: ComputeHost """
        hv2 = self.ptm.hosts_by_name['cmp2']
        """ :type hv2: ComputeHost """

        vm1 = hv1.create_vm('vm1')
        vm1.create_interface('eth0', ip_list=[IP("10.3.3.3", "8")])

        vm2 = hv2.create_vm('vm2')
        vm2.create_interface('eth0', ip_list=[IP("10.55.55.55", "8")])

        # Normally we get this from network, but just go with a mocked up port for this test
        port1 = Port("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        port2 = Port("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        virtual_host1 = Guest(vm1)
        virtual_host1.plugin_vm('eth0', port1)

        virtual_host2 = Guest(vm2)
        virtual_host2.plugin_vm('eth0', port2)

        # No virtual bridge between VMs means they should NOT talk to each other yet.
        self.assertFalse(virtual_host1.send_ping('eth0', '10.55.55.55'))

        virtual_host1.unplug_vm(port1)
        virtual_host2.unplug_vm(port2)



    def tearDown(self):
        self.ptm.shutdown()
        LinuxCLI().cmd('ip netns del vm1')

try:
    suite = unittest.TestLoader().loadTestsFromTestCase(GuestTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)
