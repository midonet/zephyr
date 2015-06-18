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

import uuid
import unittest
import logging
import datetime

from common.IP import IP
from common.CLI import LinuxCLI

from PTM.VMHost import VMHost
from PTM.ComputeHost import ComputeHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from VTM.Guest import Guest
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.tests.VirtualTopologyManagerTest import MockClient
from VTM.MNAPI import create_midonet_client

from midonetclient.api import MidonetApi
from midonetclient.bridge import Bridge
from midonetclient.port import Port
from midonetclient.tunnel_zone import TunnelZone
from midonetclient.tunnel_zone_host import TunnelZoneHost


class MNAPITest(unittest.TestCase):
    ptm = PhysicalTopologyManager(root_dir='../..', log_root_dir='./tmp/logs')

    @classmethod
    def setUpClass(cls):
        cls.ptm.configure('test-basic-config.json')
        cls.ptm.startup()

    def stest_midonet_api_ping_two_hosts_same_hv(self):
        vtm = VirtualTopologyManager(client_api_impl=create_midonet_client(),
                                     physical_topology_manager=self.ptm)

        # Set up virtual topology
        api = vtm.get_client()
        """ :type: MidonetApi"""
        tz = api.add_gre_tunnel_zone().name('main').create()
        """ :type: TunnelZone"""

        hv1 = self.ptm.hypervisors['cmp1']
        """ :type: ComputeHost"""
        hv2 = self.ptm.hypervisors['cmp2']
        """ :type: ComputeHost"""

        tz.add_tunnel_zone_host().ip_address(hv1.interfaces['eth0'].ip_list[0].ip).host_id(str(hv1.unique_id)).create()
        tz.add_tunnel_zone_host().ip_address(hv2.interfaces['eth0'].ip_list[0].ip).host_id(str(hv2.unique_id)).create()

        br = api.add_bridge().name('bridge_0').tenant_id('test1').create()
        """ :type: Bridge"""
        port1 = br.add_port().create()
        """ :type: Port"""
        port2 = br.add_port().create()
        """ :type: Port"""

        vm1 = vtm.create_vm(ip='10.1.1.2', preferred_hv_host='cmp2')
        vm2 = vtm.create_vm(ip='10.1.1.3', preferred_hv_host='cmp2')

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())

            self.assertTrue(vm1.ping(on_iface='eth0', target_ip='10.1.1.3'))
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='10.1.1.2'))

        finally:
            vm1.terminate()
            vm2.terminate()
            port1.delete()
            port2.delete()
            br.delete()

    def test_midonet_api_ping_two_hosts_diff_hv(self):
        vtm = VirtualTopologyManager(client_api_impl=create_midonet_client(),
                                     physical_topology_manager=self.ptm)

        # Set up virtual topology
        api = vtm.get_client()
        """ :type: MidonetApi"""
        tz = api.add_gre_tunnel_zone().name('main').create()
        """ :type: TunnelZone"""

        hv1 = self.ptm.hypervisors['cmp1']
        """ :type: ComputeHost"""
        hv2 = self.ptm.hypervisors['cmp2']
        """ :type: ComputeHost"""

        tz.add_tunnel_zone_host().ip_address(hv1.interfaces['eth0'].ip_list[0].ip).host_id(str(hv1.unique_id)).create()
        tz.add_tunnel_zone_host().ip_address(hv2.interfaces['eth0'].ip_list[0].ip).host_id(str(hv2.unique_id)).create()

        br = api.add_bridge().name('bridge_0').tenant_id('test1').create()
        """ :type: Bridge"""
        port1 = br.add_port().create()
        """ :type: Port"""
        port2 = br.add_port().create()
        """ :type: Port"""

        vm1 = vtm.create_vm(ip='10.1.1.2', preferred_hv_host='cmp1')
        vm2 = vtm.create_vm(ip='10.1.1.3', preferred_hv_host='cmp2')

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())

            self.assertTrue(vm1.ping(on_iface='eth0', target_ip='10.1.1.3'))
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='10.1.1.2'))

        finally:
            #import pdb
            #pdb.set_trace()

            vm1.terminate()
            vm2.terminate()
            port1.delete()
            port2.delete()
            br.delete()

    @classmethod
    def tearDownClass(cls):
        cls.ptm.shutdown()
        LinuxCLI().cmd('ip netns del vm1')

try:
    suite = unittest.TestLoader().loadTestsFromTestCase(MNAPITest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)
