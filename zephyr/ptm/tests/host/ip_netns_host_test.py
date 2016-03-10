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

import unittest

from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.ptm.host.interface import Interface
from zephyr.ptm.host.ip_netns_host import *
from zephyr.ptm.host.root_host import RootHost
from zephyr.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr.ptm.physical_topology_config import *
from zephyr.ptm.physical_topology_manager import PhysicalTopologyManager


class DummyInterface(Interface):
    def __init__(self, name, host, linked_bridge):
        super(DummyInterface, self).__init__(
            name, host, linked_bridge=linked_bridge)

    def create(self):
        self.cli.cmd('ip link add dev ' + self.get_name() + ' type dummy')
        # Add interface to the linked bridge, if there is one
        if self.linked_bridge is not None:
            self.linked_bridge.link_interface(self)


class IPNetNSHostTest(unittest.TestCase):
    def test_configure(self):
        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(
            root_dir=os.path.dirname(
                os.path.abspath(__file__)) + '/../../..', log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        hcfg = HostDef('test',
                       bridges={'br0': BridgeDef('br0')},
                       interfaces={
                           'testi': InterfaceDef(
                               'testi', [IP.make_ip('192.168.1.2')],
                               linked_bridge='br0')})
        icfg = ImplementationDef('test', 'IPNetNSHost', [])

        # Get the impl details and use that to instance a basic object
        h = IPNetNSHost(hcfg.name, ptm)
        lm.add_file_logger('test.log', 'test')
        h.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        h.config_from_ptc_def(hcfg, icfg)

        self.assertTrue(True)

    def test_boot_shutdown(self):

        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(
            root_dir=os.path.dirname(
                os.path.abspath(__file__)) + '/../../..', log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        hcfg = HostDef('test',
                       bridges={'br0': BridgeDef('br0')},
                       interfaces={
                           'testi': InterfaceDef(
                               'testi', [IP.make_ip('192.168.1.2')],
                               linked_bridge='br0')})
        icfg = ImplementationDef('test', 'IPNetNSHost', [])

        h = IPNetNSHost(hcfg.name, ptm)
        lm.add_file_logger('test.log', 'test')
        h.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        h.config_from_ptc_def(hcfg, icfg)

        h.interfaces['testi'] = DummyInterface('testi', h, h.bridges['br0'])

        h.create()

        self.assertTrue(LinuxCLI().grep_cmd('ip netns', 'test'))

        h.boot()

        h.net_up()
        h.net_finalize()

        self.assertTrue(h.cli.grep_cmd('ip l', 'testi'))  # Dummy interface
        self.assertTrue(h.cli.grep_cmd('brctl show', 'br0'))

        h.net_down()

        h.shutdown()

        self.assertFalse(h.cli.grep_cmd('brctl show', 'br0'))

        h.remove()

        self.assertFalse(LinuxCLI().grep_cmd('ip netns', 'test'))

    def test_veth_connection_between_two_hosts(self):
        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(
            root_dir=os.path.dirname(
                os.path.abspath(__file__)) + '/../../..',
            log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        h1cfg = HostDef('test1',
                        interfaces={
                            'testi': InterfaceDef(
                                'testi',
                                [IP.make_ip('192.168.1.1')])})
        i1cfg = ImplementationDef('test', 'RootHost', [])

        h2cfg = HostDef('test2',
                        interfaces={
                            'testp': InterfaceDef(
                                'testp',
                                [IP.make_ip('192.168.1.3')])})
        i2cfg = ImplementationDef('test', 'IPNetNSHost', [])

        # Host should act the same regardless of using NS or base OS
        h1 = RootHost(h1cfg.name, ptm)
        h2 = IPNetNSHost(h2cfg.name, ptm)
        h1.configure_logging(debug=True)
        h2.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        h1.config_from_ptc_def(h1cfg, i1cfg)
        h2.config_from_ptc_def(h2cfg, i2cfg)

        h1.link_interface(h1.interfaces['testi'], h2, h2.interfaces['testp'])

        h1.create()
        h2.create()
        h1.boot()
        h2.boot()
        h1.net_up()
        h2.net_up()
        h1.net_finalize()
        h2.net_finalize()

        # Linked interface should start and get peered
        self.assertTrue(h1.cli.grep_cmd('ip l', 'testi'))
        # Linked interface should start and get peered
        self.assertTrue(h2.cli.grep_cmd('ip l', 'testp'))

        self.assertTrue(h1.cli.grep_cmd('ip a | grep testi', '192.168.1.1'))
        self.assertTrue(h2.cli.grep_cmd('ip a | grep testp', '192.168.1.3'))

        h1.net_down()
        h2.net_down()

        h2.shutdown()
        h2.remove()

        self.assertFalse(h1.cli.grep_cmd('ip netns', 'test2'))

        h1.shutdown()
        h1.remove()

    def tearDown(self):
        LinuxCLI().cmd('ip netns del test')
        LinuxCLI().cmd('ip netns del test2')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')


run_unit_test(IPNetNSHostTest)
