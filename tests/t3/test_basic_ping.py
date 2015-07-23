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

from midonetclient.api import MidonetApi

from common.Exceptions import *

from VTM.Guest import Guest

from TSM.TestCase import TestCase

from tests.scenarios.TwoComputeScenario import TwoComputeScenario
from tests.scenarios.ThreeComputeEdgeScenario import ThreeComputeEdgeScenario


class TestBasicPing(TestCase):

    @staticmethod
    def supported_scenarios():
        return {TwoComputeScenario} #, ThreeComputeEdgeScenario}

    @classmethod
    def setUpClass(cls):
        """
        :type cls: TestCase
        """

        api = cls.vtm.get_client()
        tz = api.get_tunnel_zone('main')
        if tz is not None:
            tz = api.add_gre_tunnel_zone().name('main').create()

        for h in api.get_hosts(query={}):
            print "MN API Host name: " + h.get_name() + ", id: " + h.get_id()

            hv = self.ptm.hypervisors[h.get_name()]
            tzh = tz.add_tunnel_zone_host()

            tzh.ip_address(hv.interfaces['eth0'].ip_list[0].ip)
            tzh.host_id(h.get_id())
            tzh.create()

        br = api.add_bridge().name('bridge_0').tenant_id('test1').create()
        """ :type: Bridge"""
        port1 = br.add_port().create()
        """ :type: Port"""
        port2 = br.add_port().create()
        """ :type: Port"""


    def test_ping_two_vms_same_hv(self):
        api = self.vtm.get_client()
        if not isinstance(api, MidonetApi):
            raise ArgMismatchException('Need midonet client for this test')
        """ :type api: MidonetApi"""

        vm1 = self.current_scenario.vtm.create_vm('10.0.1.3', 'cmp1', 'vm1')
        """ :type: Guest"""
        vm2 = self.current_scenario.vtm.create_vm('10.0.1.4', 'cmp1', 'vm2')
        """ :type: Guest"""

        try:
            vm1.plugin_vm('eth0', port1)
            vm2.plugin_vm('eth0', port2)
        finally:
            vm1.terminate()
            vm2.terminate()

    def test_ping_two_vms_diff_hv(self):
        api = self.vtm.get_client()
        if not isinstance(api, MidonetApi):
            raise ArgMismatchException('Need midonet client for this test')
        """ :type api: MidonetApi"""

        tz = api.get_tunnel_zone('main')
        if tz is not None:
            tz = api.add_gre_tunnel_zone().name('main').create()
        """ :type tz: TunnelZone"""

        hv1 = self.ptm.hypervisors['cmp1']
        hv2 = self.ptm.hypervisors['cmp2']


        tz.add_tunnel_zone_host().ip_address(hv1.interfaces['eth0'].ip_list[0].ip).host_id(str(hv1.unique_id)).create()
        tz.add_tunnel_zone_host().ip_address(hv2.interfaces['eth0'].ip_list[0].ip).host_id(str(hv2.unique_id)).create()

        br = api.add_bridge().name('bridge_0').tenant_id('test1').create()
        """ :type: Bridge"""
        port1 = br.add_port().create()
        """ :type: Port"""
        port2 = br.add_port().create()
        """ :type: Port"""

        vm1 = self.current_scenario.vtm.create_vm('10.0.1.3', 'cmp1', 'vm1')
        """ :type: Guest"""
        vm2 = self.current_scenario.vtm.create_vm('10.0.1.4', 'cmp2', 'vm2')
        """ :type: Guest"""

        try:
            vm1.plugin_vm('eth0', port1)
            vm2.plugin_vm('eth0', port2)
        finally:
            vm1.terminate()
            vm2.terminate()


