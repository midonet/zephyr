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
import os

from common.IP import IP
from common.CLI import LinuxCLI
from common.LogManager import LogManager

from PTM.VMHost import VMHost
from PTM.ComputeHost import ComputeHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from VTM.Guest import Guest
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.MNAPI import create_midonet_client, setup_main_bridge, setup_main_tunnel_zone

from midonetclient.api import MidonetApi
from midonetclient.bridge import Bridge
from midonetclient.port import Port
from midonetclient.tunnel_zone import TunnelZone
from midonetclient.tunnel_zone_host import TunnelZoneHost

class MNAPITest(unittest.TestCase):
    lm=LogManager('test-logs')
    ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

    @classmethod
    def setUpClass(cls):
        cls.ptm.configure(os.path.dirname(os.path.abspath(__file__)) + '/test-basic-config.json')
        cls.ptm.configure_logging(debug=True)
        logging.getLogger("midonetclient.api_lib").addHandler(logging.StreamHandler())
        cls.ptm.startup()

    def test_midonet_api_ping_two_hosts_same_hv(self):
        vtm = VirtualTopologyManager(client_api_impl=create_midonet_client(),
                                     physical_topology_manager=self.ptm)


        # Set up virtual topology
        api = vtm.get_client()
        """ :type: MidonetApi"""

        logger = self.ptm.log_manager.add_tee_logger('MNAPITest', 'mnapi-test-logger',
                                                     file_log_level=logging.DEBUG,
                                                     stdout_log_level=logging.DEBUG)

        tz = setup_main_tunnel_zone(api,
                                    {h.name: h.interfaces['eth0'].ip_list[0].ip
                                     for h in self.ptm.hypervisors.itervalues()},
                                    logger)
        main_bridge = setup_main_bridge(api)
        """ :type: Bridge"""

        port1 = main_bridge.add_port().create()
        """ :type: Port"""
        port2 = main_bridge.add_port().create()
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
            main_bridge.delete()

    def test_midonet_api_ping_two_hosts_diff_hv(self):
        vtm = VirtualTopologyManager(client_api_impl=create_midonet_client(),
                                     physical_topology_manager=self.ptm)

        # Set up virtual topology
        api = vtm.get_client()
        """ :type: MidonetApi"""
        logger = self.ptm.log_manager.add_tee_logger('MNAPITest', 'mnapi-test-logger',
                                                     file_log_level=logging.DEBUG,
                                                     stdout_log_level=logging.DEBUG)
        tz = setup_main_tunnel_zone(api,
                                    {h.name: h.interfaces['eth0'].ip_list[0].ip
                                     for h in self.ptm.hypervisors.itervalues()},
                                    logger)
        main_bridge = setup_main_bridge(api)
        """ :type: Bridge"""

        port1 = main_bridge.add_port().create()
        """ :type: Port"""
        port2 = main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = vtm.create_vm(ip='10.1.1.2', preferred_hv_host='cmp1')
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
            main_bridge.delete()

    @classmethod
    def tearDownClass(cls):
        cls.ptm.shutdown()
        LinuxCLI().cmd('ip netns del vm1')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(MNAPITest)
