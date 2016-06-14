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

import os
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.vtm import virtual_topology_manager
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.application import midolman
from zephyr_ptm.ptm.fixtures import midonet_setup_fixture
from zephyr_ptm.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr_ptm.ptm.physical_topology_config import *
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../../..'


class VMHostTest(unittest.TestCase):
    ptm_i = None
    ptm = None
    vtm = None
    hv_app = None
    hypervisor = None
    main_bridge = None

    @classmethod
    def setUpClass(cls):
        try:
            lm = LogManager('./test-logs')
            cls.ptm_i = ConfiguredHostPTMImpl(
                root_dir=ROOT_DIR,
                log_manager=lm)
            cls.ptm_i.configure_logging(log_file_name='test-ptm.log',
                                        debug=True)
            cls.ptm = PhysicalTopologyManager(cls.ptm_i)
            path = os.path.abspath(__file__)
            dir_path = os.path.dirname(path)
            cls.ptm.configure(
                config_file='test-basic-ptm.json',
                config_dir=dir_path + '/..')
            cls.ptm.startup()

            cls.vtm = virtual_topology_manager.VirtualTopologyManager(
                client_api_impl=midonet_setup_fixture.create_midonet_client(),
                physical_topology_manager=cls.ptm)

            # Set up virtual topology
            api = cls.vtm.get_client()
            """ :type: MidonetApi"""

            tunnel_zone_host_map = {}
            for host_name, host in cls.ptm.impl_.hosts_by_name.iteritems():
                # On each host, check if there is at least one
                # Midolman app running
                for app in host.applications:
                    if isinstance(app, midolman.Midolman):
                        # If so, add the host and its eth0 interface
                        # to the tunnel zone map and move on to next host
                        tunnel_zone_host_map[host.name] = (
                            host.interfaces['eth0'].ip_list[0].ip)
                        break
            midonet_setup_fixture.setup_main_tunnel_zone(
                api,
                tunnel_zone_host_map,
                cls.ptm_i.LOG)

            cls.main_bridge = midonet_setup_fixture.setup_main_bridge(api)
            """ :type: Bridge"""
            cls.hypervisor = cls.ptm_i.hosts_by_name['cmp1']
            hv_app_type = application.APPLICATION_TYPE_HYPERVISOR
            cls.hv_app = cls.hypervisor.applications_by_type[hv_app_type][0]

        except (KeyboardInterrupt, Exception):
            cls.ptm.shutdown()
            raise

    def test_create_vm(self):

        vm_host = self.hv_app.create_vm('test_vm')
        self.assertIs(vm_host, self.hv_app.get_vm('test_vm'))

        vm_host.create()
        vm_host.boot()
        vm_host.net_up()
        vm_host.net_finalize()

        vm_host.shutdown()
        vm_host.remove()

    def test_create_vm_interface(self):

        vm_host = self.hv_app.create_vm('test_vm')
        self.assertIs(vm_host, self.hv_app.get_vm('test_vm'))

        vm_host.create_interface('eth0', ip_list=[IP('10.50.50.3')])

        self.assertTrue(vm_host.cli.grep_cmd('ip l', 'eth0'))
        self.assertTrue(self.hypervisor.cli.grep_cmd('ip l', 'test_vmeth0'))

        vm_host.shutdown()
        vm_host.remove()

    def test_packet_communication(self):
        vm_host1 = self.hv_app.create_vm('test_vm1')
        try:

            vm_host1.create_interface('eth0', ip_list=[IP('10.50.50.3')])

            vm_host1.start_capture('lo', save_dump_file=True,
                                   save_dump_filename='tcp.vmhost.out')

            ping_ret = vm_host1.ping('10.50.50.3')
            vm_host1.send_tcp_packet(iface='lo', dest_ip='10.50.50.3',
                                     source_port=6015, dest_port=6055)

            ret1 = vm_host1.capture_packets('lo', count=1, timeout=5)
            vm_host1.capture_packets('lo', count=1, timeout=5)

            vm_host1.stop_capture('lo')

            self.assertTrue(ping_ret)
            self.assertEqual(1, len(ret1))

        finally:
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
