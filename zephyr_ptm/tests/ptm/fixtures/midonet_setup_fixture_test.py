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

import logging
import os
import time
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager
from zephyr_ptm.ptm.application.midolman import Midolman
from zephyr_ptm.ptm.fixtures import midonet_setup_fixture
from zephyr_ptm.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../../..'


class MNAPITest(unittest.TestCase):
    def __init__(self, method_name):
        super(MNAPITest, self).__init__(methodName=method_name)
        self.ptm_i = None
        self.ptm = None
        self.vtm = None
        self.main_bridge = None

    def setUp(self):
        try:
            lm = LogManager('./test-logs')
            self.ptm_i = ConfiguredHostPTMImpl(
                root_dir=ROOT_DIR,
                log_manager=lm)
            self.ptm_i.configure_logging(log_file_name='test-ptm.log',
                                         debug=True)
            self.ptm = PhysicalTopologyManager(self.ptm_i)
            path = os.path.abspath(__file__)
            dir_path = os.path.dirname(path)
            self.ptm.configure(
                config_file='test-basic-config.json',
                config_dir=dir_path)
            logging.getLogger("midonetclient.api_lib").addHandler(
                logging.StreamHandler())
            self.ptm.startup()

            self.vtm = VirtualTopologyManager(
                client_api_impl=midonet_setup_fixture.create_midonet_client(),
                physical_topology_manager=self.ptm)

            # Set up virtual topology
            api = self.vtm.get_client()
            """ :type: MidonetApi"""

            logger = self.ptm.log_manager.add_tee_logger(
                'MNAPITest', 'mnapi-test-logger',
                file_log_level=logging.DEBUG,
                stdout_log_level=logging.DEBUG)

            tunnel_zone_host_map = {}
            for host_name, host in self.ptm.impl_.hosts_by_name.iteritems():
                # On each host, check if there is at least one
                # Midolman app running
                for app in host.applications:
                    if isinstance(app, Midolman):
                        # If so, add the host and its eth0 interface
                        # to the tunnel zone map and move on to next host
                        tunnel_zone_host_map[host.name] = (
                            host.interfaces['eth0'].ip_list[0].ip)
                        break
            midonet_setup_fixture.setup_main_tunnel_zone(
                api,
                tunnel_zone_host_map,
                logger)

            self.main_bridge = midonet_setup_fixture.setup_main_bridge(api)
            """ :type: Bridge"""

        except (KeyboardInterrupt, Exception):
            self.ptm.shutdown()
            raise
    #
    # def test_midonet_api_ping_two_hosts_same_hv(self):
    #
    #     port1 = self.main_bridge.add_port().create()
    #     """ :type: Port"""
    #     port2 = self.main_bridge.add_port().create()
    #     """ :type: Port"""
    #
    #     vm1 = self.vtm.create_vm(ip='10.1.1.2', hv_host='cmp1')
    #     vm2 = self.vtm.create_vm(ip='10.1.1.3', hv_host='cmp1')
    #
    #     try:
    #         vm1.plugin_vm('eth0', port1.get_id())
    #         vm2.plugin_vm('eth0', port2.get_id())
    #         time.sleep(1)
    #         self.assertTrue(vm1.ping(target_ip='10.1.1.3', on_iface='eth0'))
    #         self.assertTrue(vm2.ping(target_ip='10.1.1.2', on_iface='eth0'))
    #
    #     finally:
    #         vm1.terminate()
    #         vm2.terminate()
    #         port1.delete()
    #         port2.delete()

    def test_midonet_api_ping_two_hosts_diff_hv(self):

        port1 = self.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = self.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = self.vtm.create_vm(ip='172.16.55.2', hv_host='cmp1')
        vm2 = self.vtm.create_vm(ip='172.16.55.3', hv_host='cmp2')

        try:
            vm1.plugin_vm('eth0', port1.get_id())
            vm2.plugin_vm('eth0', port2.get_id())
            time.sleep(1)
            self.assertTrue(vm1.ping(target_ip='172.16.55.3', on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip='172.16.55.2', on_iface='eth0'))

        finally:
            vm1.terminate()
            vm2.terminate()
            port1.delete()
            port2.delete()

    def tearDown(self):
        LinuxCLI().cmd('ip netns del vm1')
        self.main_bridge.delete()
        self.ptm.shutdown()

run_unit_test(MNAPITest)
