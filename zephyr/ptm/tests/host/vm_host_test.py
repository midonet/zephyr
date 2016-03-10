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
from zephyr.ptm.host.ip_netns_host import IPNetNSHost
from zephyr.ptm.host.root_host import RootHost
from zephyr.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr.ptm.physical_topology_config import *
from zephyr.ptm.physical_topology_manager import PhysicalTopologyManager


class VMHostTest(unittest.TestCase):

    def setUp(self):
        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(
            root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..',
            log_manager=lm)
        ptm = PhysicalTopologyManager(ptm_i)

        self.hypervisor = None
        self.root_host = None

        root_hostcfg = HostDef(
            'root',
            interfaces={'hveth0': InterfaceDef('hveth0')})
        root_host_implcfg = ImplementationDef('test', 'ptm.host.RootHost', [])

        hypervisorcfg = HostDef(
            'hv',
            interfaces={'eth0': InterfaceDef('eth0', [IP('192.168.1.3')])})
        hypervisor_implcfg = ImplementationDef(
            'test', 'ptm.host.IPNetNSHost',
            [ApplicationDef('ptm.application.Midolman', id=1)])

        self.root_host = RootHost(root_hostcfg.name, ptm)
        self.hypervisor = IPNetNSHost(hypervisorcfg.name, ptm)

        lm.add_file_logger('test.log', 'test')
        self.root_host.configure_logging(debug=True)
        self.hypervisor.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        self.root_host.config_from_ptc_def(root_hostcfg, root_host_implcfg)
        self.hypervisor.config_from_ptc_def(hypervisorcfg, hypervisor_implcfg)

        self.root_host.link_interface(
            self.root_host.interfaces['hveth0'],
            self.hypervisor, self.hypervisor.interfaces['eth0'])

        self.root_host.create()
        self.hypervisor.create()
        self.root_host.boot()
        self.hypervisor.boot()
        self.root_host.net_up()
        self.hypervisor.net_up()
        self.root_host.net_finalize()
        self.hypervisor.net_finalize()

        self.mm_app = self.hypervisor.applications[0]
        """ :type: Midolman"""

    def test_create_vm(self):

        vm_host = self.mm_app.create_vm('test_vm')
        self.assertIs(vm_host, self.mm_app.get_vm('test_vm'))

        vm_host.create()
        vm_host.boot()
        vm_host.net_up()
        vm_host.net_finalize()

        vm_host.shutdown()
        vm_host.remove()

    def test_create_vm_interface(self):

        vm_host = self.mm_app.create_vm('test_vm')
        self.assertIs(vm_host, self.mm_app.get_vm('test_vm'))

        vm_host.create_interface('eth0', ip_list=[IP('10.50.50.3')])

        self.assertTrue(vm_host.cli.grep_cmd('ip l', 'eth0'))
        self.assertTrue(self.hypervisor.cli.grep_cmd('ip l', 'test_vmeth0'))

        vm_host.shutdown()
        vm_host.remove()

    def test_packet_communication(self):
        vm_host1 = self.mm_app.create_vm('test_vm1')
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

    def tearDown(self):
        self.root_host.net_down()
        self.hypervisor.net_down()
        self.hypervisor.shutdown()
        self.root_host.shutdown()
        self.hypervisor.remove()
        self.root_host.remove()
        LinuxCLI().cmd('ip netns del test_vm')
        LinuxCLI().rm('tcp.vmhost.out')


run_unit_test(VMHostTest)
