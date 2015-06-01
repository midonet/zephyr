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


from VTM.Guest import Guest
from VTM.VirtualTopologyConfig import VirtualTopologyConfig
from VTM.tests.VirtualTopologyConfigTest import MockClient
from PTM.VMHost import VMHost
from PTM.ComputeHost import ComputeHost
from PTM.MNRootServer import MNRootServer
from VTM.Network import Network
from VTM.Port import Port

import logging
import datetime

class GuestTest(unittest.TestCase):

    def test_host_plugin_vm(self):
        vtc = VirtualTopologyConfig(client_api_impl=MockClient)
        test_system = MNRootServer()
        hv = test_system.config_compute(HostDef('cmp1', [InterfaceDef(name='eth0', ip_list=[IPDef('2.2.2.2', '32')])]))
        vm = test_system.config_vm(VMDef('cmp1', HostDef('vm1', [InterfaceDef(name='eth0',
                                                                         ip_list=[IPDef('3.3.3.3', '32')])])))

        # Normally we get this from network, but just go with a mocked up port for this test
        port = Port("fe6707e3-9c99-4529-b059-aa669d1463bb")

        virtual_host = Guest(vtc, vm)
        virtual_host.plugin_vm('eth0', port)
        self.assertEquals(virtual_host.open_ports_by_interface['eth0'], port)


    def test_host_unplug_vm(self):
        vtc = VirtualTopologyConfig(client_api_impl=MockClient)
        test_system = MNRootServer()
        test_system.config_compute(HostDef('cmp1', [InterfaceDef(name='eth0', ip_list=[IPDef('2.2.2.2', '32')])]))
        vm = test_system.config_vm(VMDef('cmp1', HostDef('vm1', [InterfaceDef(name='eth0',
                                                                         ip_list=[IPDef('3.3.3.3', '32')])])))

        # Normally we get this from network, but just go with a mocked up port for this test
        port = Port("fe6707e3-9c99-4529-b059-aa669d1463bb")

        virtual_host = Guest(vtc, vm)
        virtual_host.plugin_vm('eth0', port)

        virtual_host.unplug_vm(port)
        self.assertTrue('eth0' not in virtual_host.open_ports_by_interface)

try:
    suite = unittest.TestLoader().loadTestsFromTestCase(HostTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)
