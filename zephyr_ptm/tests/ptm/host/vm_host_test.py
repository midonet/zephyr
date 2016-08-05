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

import json
import os
import time
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common import exceptions
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.midonet import mn_api_utils
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.application import midolman
from zephyr_ptm.ptm.config import version_config
from zephyr_ptm.ptm.physical_topology_config import *
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager

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


class VMHostTest(unittest.TestCase):
    ptm = None
    hv_app = None
    hypervisor = None
    main_bridge = None

    @classmethod
    def setUpClass(cls):
        try:
            lm = LogManager('./test-logs')
            cls.ptm = PhysicalTopologyManager(
                root_dir=ROOT_DIR,
                log_manager=lm)
            cls.ptm.configure_logging(log_file_name='test-ptm.log',
                                      debug=True)

            path = os.path.abspath(__file__)
            dir_path = os.path.dirname(path)
            cls.ptm.configure(
                config_file=dir_path + '/../test-basic-ptm.json')
            cls.ptm.startup()

            print_json('./underlay-config.json', cls.ptm, True, './test-logs')

            # Set up virtual topology
            api = mn_api_utils.create_midonet_client(
                version_config.ConfigMap.get_configured_parameter(
                    'param_midonet_api_url'))
            """ :type: MidonetApi"""

            tunnel_zone_host_map = {}
            for host_name, host in cls.ptm.hosts_by_name.iteritems():
                # On each host, check if there is at least one
                # Midolman app running
                for app in host.applications:
                    if isinstance(app, midolman.Midolman):
                        # If so, add the host and its eth0 interface
                        # to the tunnel zone map and move on to next host
                        tunnel_zone_host_map[host.name] = (
                            host.interfaces['eth0'].ip_list[0].ip)
                        break
            mn_api_utils.setup_main_tunnel_zone(
                api,
                tunnel_zone_host_map,
                cls.ptm.LOG)

            cls.main_bridge = mn_api_utils.setup_main_bridge(api)
            """ :type: Bridge"""
            cls.hypervisor = cls.ptm.hosts_by_name['cmp1']
            hv_app_type = application.APPLICATION_TYPE_HYPERVISOR
            cls.hv_app = cls.hypervisor.applications_by_type[hv_app_type][0]

        except (KeyboardInterrupt, Exception):
            cls.ptm.shutdown()
            raise

    def test_create_vm(self):

        vm_host = self.hv_app.create_vm('test_vm')
        self.assertIs(vm_host, self.hv_app.get_vm('test_vm'))

        vm_host2 = self.hv_app.create_vm('test_vm')

        vm_list = self.hv_app.get_vm('test_vm')
        self.assertTrue(isinstance(vm_list, list))
        self.assertIs(vm_host, vm_list[0])
        self.assertIs(vm_host2, vm_list[1])

        vm_host.create()
        vm_host.boot()
        vm_host.net_up()
        vm_host.net_finalize()

        vm_host.shutdown()
        vm_host.remove()

        vm_list = self.hv_app.get_vm('test_vm')

        self.assertIs(vm_host2, vm_list)

        vm_host2.shutdown()

        self.assertIsNone(self.hv_app.get_vm('test_vm'))

    def test_cross_vm_communication(self):
        vm_host1 = self.hv_app.create_vm('test_vm1')
        vm_host2 = self.hv_app.create_vm('test_vm2')
        try:
            self.hypervisor.create_tap_interface_for_vm(
                tap_iface_name='tapvm1eth0', vm_host=vm_host1,
                vm_iface_name='eth0', vm_ip_list=[IP('10.50.50.3')])

            self.hypervisor.create_tap_interface_for_vm(
                tap_iface_name='tapvm2eth0', vm_host=vm_host2,
                vm_iface_name='eth0', vm_ip_list=[IP('10.50.50.4')])

            port1 = self.main_bridge.add_port().create()
            port2 = self.main_bridge.add_port().create()

            self.hv_app.plugin_iface_to_network(
                tap_iface='tapvm1eth0', port_id=port1.get_id())
            self.hv_app.plugin_iface_to_network(
                tap_iface='tapvm2eth0', port_id=port2.get_id())

            self.assertTrue(vm_host2.ping('10.50.50.3'))

            vm_host1.start_echo_server(ip_addr='')
            deadline = time.time() + 10
            connected = False
            resp = ''
            while not connected:
                try:
                    resp = vm_host2.send_echo_request(dest_ip='10.50.50.3')
                    connected = True
                except exceptions.SubprocessFailedException:
                    if time.time() > deadline:
                        raise exceptions.SubprocessTimeoutException(
                            'Failed to send TCP echo to VM2')
                    time.sleep(0)
            self.assertEqual('ping:pong', resp)

        finally:
            vm_host2.shutdown()
            vm_host2.remove()
            vm_host1.stop_echo_server(ip_addr='')
            vm_host1.shutdown()
            vm_host1.remove()

    def test_basic_file_access(self):
        log_files = self.hypervisor.fetch_resources_from_apps(
            resource_name='log')
        self.assertEqual(1, len(log_files))
        self.assertGreater(len(log_files[0]), 0)

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip netns del vm1')
        cls.main_bridge.delete()
        cls.ptm.shutdown()
        LinuxCLI().cmd('rm -f tcp.vmhost.out')


run_unit_test(VMHostTest)
