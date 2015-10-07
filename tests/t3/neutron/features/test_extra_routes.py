__author__ = 'micucci'
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

import neutronclient as neutron_client

from common.Exceptions import *

from VTM.Guest import Guest

from TSM.TestCase import TestCase

from tests.scenarios.TwoComputeScenario import TwoComputeScenario


class TestBasicPing(TestCase):
    api = None
    """ :type: neutron_client.client """

    @staticmethod
    def supported_scenarios():
        return {TwoComputeScenario}

    @classmethod
    def setUpClass(cls):
        cls.api = cls.vtm.get_client()
        if not isinstance(cls.api, MidonetApi):
            raise ArgMismatchException('Need midonet client for this test')

        setup_main_tunnel_zone(cls.api,
                               {h.name: h.interfaces['eth0'].ip_list[0].ip
                                for h in cls.ptm.hypervisors.itervalues()},
                               cls.setup_logger)
        cls.main_bridge = setup_main_bridge(cls.api)

    def test_ping_two_vms_same_hv(self):

        port1 = TestBasicPing.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = TestBasicPing.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = TestBasicPing.vtm.create_vm('10.0.1.3', 'cmp1', 'vm1')
        """ :type: Guest"""
        vm2 = TestBasicPing.vtm.create_vm('10.0.1.4', 'cmp1', 'vm2')
        """ :type: Guest"""

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())

            vm1.ping(on_iface='eth0', target_ip='10.0.1.4')

        finally:
            vm1.terminate()
            vm2.terminate()

    def test_ping_two_vms_diff_hv(self):

        port1 = TestBasicPing.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = TestBasicPing.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = TestBasicPing.vtm.create_vm('10.0.1.3', 'cmp1', 'vm1')
        """ :type: Guest"""
        vm2 = TestBasicPing.vtm.create_vm('10.0.1.4', 'cmp2', 'vm2')
        """ :type: Guest"""

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())

            vm1.ping(on_iface='eth0', target_ip='10.0.1.4')
        finally:
            vm1.terminate()
            vm2.terminate()


