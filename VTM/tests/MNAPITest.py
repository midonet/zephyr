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

import unittest
import logging
import os
import time

from common.CLI import LinuxCLI
from common.LogManager import LogManager
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.application.Midolman import Midolman
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.MNAPI import create_midonet_client, setup_main_bridge, setup_main_tunnel_zone


class MNAPITest(unittest.TestCase):
    lm = LogManager('test-logs')
    ptm_i = ConfiguredHostPTMImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)
    ptm = PhysicalTopologyManager(ptm_i)
    vtm = None
    main_bridge = None

    @classmethod
    def setUpClass(cls):
        try:
            cls.ptm.configure(os.path.dirname(os.path.abspath(__file__)) + '/test-basic-config.json')
            cls.ptm_i.configure_logging(debug=True)
            logging.getLogger("midonetclient.api_lib").addHandler(logging.StreamHandler())
            cls.ptm.startup()

            cls.vtm = VirtualTopologyManager(client_api_impl=create_midonet_client(),
                                             physical_topology_manager=cls.ptm)

            # Set up virtual topology
            api = cls.vtm.get_client()
            """ :type: MidonetApi"""

            logger = cls.ptm.log_manager.add_tee_logger('MNAPITest', 'mnapi-test-logger',
                                                        file_log_level=logging.DEBUG,
                                                        stdout_log_level=logging.DEBUG)

            tunnel_zone_host_map = {}
            for host_name, host in cls.ptm.impl_.hosts_by_name.iteritems():
                # On each host, check if there is at least one Midolman app running
                for app in host.applications:
                    if isinstance(app, Midolman):
                        # If so, add the host and its eth0 interface to the tunnel zone map
                        # and move on to next host
                        tunnel_zone_host_map[host.name] = host.interfaces['eth0'].ip_list[0].ip
                        break
            setup_main_tunnel_zone(api,
                                   tunnel_zone_host_map,
                                   logger)

            cls.main_bridge = setup_main_bridge(api)
            """ :type: Bridge"""

        except:
            cls.ptm.shutdown()
            raise

    def test_midonet_api_ping_two_hosts_same_hv(self):

        port1 = self.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = self.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = self.vtm.create_vm(ip='10.1.1.2', hv_host='cmp2')
        vm2 = self.vtm.create_vm(ip='10.1.1.3', hv_host='cmp2')

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())
            time.sleep(1)
            self.assertTrue(vm1.ping(target_ip='10.1.1.3', on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip='10.1.1.2', on_iface='eth0'))

        finally:
            vm1.terminate()
            vm2.terminate()
            port1.delete()
            port2.delete()

    def test_midonet_api_ping_two_hosts_diff_hv(self):

        port1 = self.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = self.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = self.vtm.create_vm(ip='10.1.1.2', hv_host='cmp1')
        vm2 = self.vtm.create_vm(ip='10.1.1.3', hv_host='cmp2')

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())
            time.sleep(1)
            self.assertTrue(vm1.ping(target_ip='10.1.1.3', on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip='10.1.1.2', on_iface='eth0'))

        finally:
            vm1.terminate()
            vm2.terminate()
            port1.delete()
            port2.delete()

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip netns del vm1')
        cls.main_bridge.delete()
        cls.ptm.shutdown()

from CBT.UnitTestRunner import run_unit_test
run_unit_test(MNAPITest)
