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

import os
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class PhysicalTopologyManagerTest(unittest.TestCase):

    def test_configure(self):
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(
            root_dir=ROOT_DIR,
            log_manager=lm)
        ptm.configure_logging(log_file_name="test-ptm.log", debug=True)

        ptm.configure(config_file=dir_path + '/test-config.json')

        self.assertTrue('zoo1' in ptm.hosts_by_name)
        self.assertTrue('edge1' in ptm.hosts_by_name)

        self.assertEqual('test-config.json', ptm.config_file)

        self.assertEqual(ptm.host_by_start_order[0][0].name, 'root')
        self.assertEqual(ptm.host_by_start_order[1][0].name, 'external1')
        self.assertEqual(ptm.host_by_start_order[2][0].name, 'test-host1')
        self.assertEqual(ptm.host_by_start_order[2][1].name, 'test-host2')
        self.assertEqual(ptm.host_by_start_order[3][0].name, 'edge1')
        self.assertEqual(ptm.host_by_start_order[4][0].name, 'zoo1')
        self.assertEqual(ptm.host_by_start_order[5][0].name, 'net1')
        self.assertEqual(ptm.host_by_start_order[6][0].name, 'cmp1')

        zk_host = ptm.hosts_by_name['zoo1']

        self.assertTrue('eth0' in zk_host.interfaces)

        root_host = ptm.hosts_by_name['root']

        self.assertTrue('zoo1eth0' in root_host.interfaces)

    def test_print_config(self):
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=ROOT_DIR, log_manager=lm)
        ptm.configure_logging(log_file_name="test-ptm.log", debug=True)

        ptm.configure(config_file=dir_path + '/test-config.json')

        ptm.print_config()
        self.assertTrue(True)

    def test_boot(self):

        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=ROOT_DIR, log_manager=lm)
        ptm.configure_logging(log_file_name="test-ptm.log", debug=True)

        ptm.configure(config_file=dir_path + '/test-config.json')

        for l in ptm.host_by_start_order:
            for h in l:
                h.create()
        for l in ptm.host_by_start_order:
            for h in l:
                h.boot()
        for l in ptm.host_by_start_order:
            for h in l:
                h.net_up()
        for l in ptm.host_by_start_order:
            for h in l:
                h.net_finalize()

        self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'zoo1'))
        self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'test-host1'))
        root_host = ptm.hosts_by_name['root']
        test_host1 = ptm.hosts_by_name['test-host1']

        self.assertTrue(root_host.cli.grep_cmd('ip l', 'th1eth1'))
        self.assertTrue(test_host1.cli.grep_cmd('ip l', 'eth1'))

        for l in reversed(ptm.host_by_start_order):
            for h in l:
                h.net_down()
        for l in reversed(ptm.host_by_start_order):
            for h in l:
                h.shutdown()
        for l in reversed(ptm.host_by_start_order):
            for h in l:
                h.remove()

        self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'zoo1'))
        self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'test-host1'))

    def test_startup(self):
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=ROOT_DIR, log_manager=lm)
        ptm.configure_logging(log_file_name="test-ptm.log", debug=True)

        try:
            ptm.configure(config_file=dir_path + '/test-config.json')
            ptm.startup()

            self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'zoo1'))
            self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'test-host1'))
            root_host = ptm.hosts_by_name['root']
            test_host1 = ptm.hosts_by_name['test-host1']

            self.assertTrue(root_host.cli.grep_cmd('ip l', 'th1eth1'))
            self.assertTrue(test_host1.cli.grep_cmd('ip l', 'eth1'))

            ptm.shutdown()

            self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'zoo1'))
            self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'test-host1'))
        except Exception:
            LinuxCLI().copy_file(
                '/var/log/midolman.1/midolman.log',
                './test-logs/PhysicalTopologyManagerTest-midolman.log')
            raise

    def tearDown(self):
        LinuxCLI().cmd('ip netns del cmp1')
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip netns del edge1')
        LinuxCLI().cmd('ip netns del external1')
        LinuxCLI().cmd('ip netns del test-host1')
        LinuxCLI().cmd('ip netns del test-host2')
        LinuxCLI().cmd('ip l set dev br0 down')
        LinuxCLI().cmd('ip l set dev brv0 down')
        LinuxCLI().cmd('ip l del zoo1eth0')
        LinuxCLI().cmd('ip l del cmp1eth0')
        LinuxCLI().cmd('ip l del th1eth0')
        LinuxCLI().cmd('ip l del th1eth1')
        LinuxCLI().cmd('ip l del th2eth0')
        LinuxCLI().cmd('brctl delbr br0')
        LinuxCLI().cmd('brctl delbr brv0')


run_unit_test(PhysicalTopologyManagerTest)
