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

import json
import os
import time
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common import log_manager
from zephyr.common.utils import run_unit_test
from zephyr.midonet import mn_api_utils
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager
from zephyr_ptm.ptm.config import version_config
from zephyr_ptm.ptm import physical_topology_manager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../../..'


def print_json(json_out_file, ptm_imp, debug, log_dir):
    config_map = {
        'debug': debug,
        'log_dir': log_dir,
        'ptm_log_file': ptm_imp.log_file_name,
        'underlay_system':
            "zephyr_ptm.ptm.underlay.ptm_underlay_system.PTMUnderlaySystem",
        'topology_config_file': ptm_imp.topo_file,
        'root_dir': ptm_imp.root_dir,
        'api_url':
            version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url')
    }
    out_str = json.dumps(config_map)
    with open(json_out_file, 'w') as fp:
        fp.write(out_str)


class MNAPITest(unittest.TestCase):
    def __init__(self, method_name):
        super(MNAPITest, self).__init__(methodName=method_name)
        self.vtm = None
        self.ptm = None
        self.main_bridge = None

    def setUp(self):
        try:
            path = os.path.abspath(__file__)
            dir_path = os.path.dirname(path)

            lm = log_manager.LogManager('./test-logs')

            self.ptm = physical_topology_manager.PhysicalTopologyManager(
                root_dir=ROOT_DIR,
                log_manager=lm)
            self.ptm.configure_logging(
                log_file_name="test-ptm.log", debug=True)
            self.ptm.configure(dir_path + "/../test-basic-ptm.json")
            self.ptm.startup()

            print_json('./underlay-config.json', self.ptm, True, './test-logs')

            self.vtm = VirtualTopologyManager(
                client_api_impl=mn_api_utils.create_midonet_client(
                    version_config.ConfigMap.get_configured_parameter(
                        'param_midonet_api_url')))
            self.vtm.configure_logging(debug=True)
            self.vtm.read_underlay_config('./underlay-config.json')

            # Set up virtual topology
            api = self.vtm.get_client()
            """ :type: MidonetApi"""

            self.main_bridge = mn_api_utils.setup_main_bridge(api)
            """ :type: Bridge"""

        except (KeyboardInterrupt, Exception):
            self.ptm.shutdown()
            raise

    def test_midonet_api_ping_two_hosts_same_hv(self):
        port1 = self.main_bridge.add_port().create()
        """ :type: Port"""
        port2 = self.main_bridge.add_port().create()
        """ :type: Port"""

        vm1 = self.vtm.create_vm()
        vm2 = self.vtm.create_vm(hv_host=vm1.get_hypervisor_name())

        try:
            vm1.plugin_port('eth0', port1.get_id())
            vm1.setup_vm_network(ip_addr='10.1.1.2/24')
            vm2.plugin_port('eth0', port2.get_id())
            vm2.setup_vm_network(ip_addr='10.1.1.3/24')
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

        vm1 = self.vtm.create_vm()
        vm2 = self.vtm.create_vm(hv_host='!' + vm1.get_hypervisor_name())

        try:
            vm1.plugin_port('eth0', port1.get_id())
            vm1.setup_vm_network(ip_addr='172.16.55.2/24')
            vm2.plugin_port('eth0', port2.get_id())
            vm2.setup_vm_network(ip_addr='172.16.55.3/24')
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
