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

from zephyr.cbt import version_config
from zephyr.common.cli import LinuxCLI
from zephyr.common.ip import IP
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.ptm.host.ip_netns_host import IPNetNSHost
from zephyr.ptm.host.root_host import RootHost
from zephyr.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr.ptm.physical_topology_config import ApplicationDef
from zephyr.ptm.physical_topology_config import BridgeDef
from zephyr.ptm.physical_topology_config import HostDef
from zephyr.ptm.physical_topology_config import ImplementationDef
from zephyr.ptm.physical_topology_config import InterfaceDef
from zephyr.ptm.physical_topology_manager import PhysicalTopologyManager


class MidonetAPITest(unittest.TestCase):
    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(
            root_dir=os.path.dirname(
                os.path.abspath(__file__)) + '/../../..',
            log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        root_cfg = HostDef('root',
                           bridges={
                               'br0': BridgeDef(
                                   'br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={
                               'zoo1eth0': InterfaceDef(
                                   'zoo1eth0', linked_bridge='br0'),
                               'cmp1eth0': InterfaceDef(
                                   'cmp1eth0', linked_bridge='br0')})
        zoo1_cfg = HostDef('zoo1',
                           interfaces={
                               'eth0': InterfaceDef(
                                   'eth0', ip_addresses=[IP('10.0.0.2')])})
        cmp1_cfg = HostDef('cmp1',
                           interfaces={
                               'eth0': InterfaceDef(
                                   'eth0', ip_addresses=[IP('10.0.0.8')])})
        net_cfg = HostDef('net')

        zoo1_icfg = ImplementationDef(
            'zoo1', 'ptm.host.IPNetNSHost',
            [ApplicationDef(
                'ptm.application.Zookeeper', id='1',
                zookeeper_ips=['10.0.0.2'])])
        cmp1_icfg = ImplementationDef(
            'cmp1', 'ptm.host.IPNetNSHost',
            [ApplicationDef(
                'ptm.application.Midolman', id='1',
                zookeeper_ips=['10.0.0.2'], cassandra_ips=[])])
        root_icfg = ImplementationDef(
            'root', 'ptm.host.RootHost', [])
        net_icfg = ImplementationDef(
            'net1', 'ptm.host.IPNetNSHost',
            [ApplicationDef(
                'ptm.application.MidonetAPI',
                zookeeper_ips=['10.0.0.2'])])

        root = RootHost('root', ptm)
        zoo1 = IPNetNSHost(zoo1_cfg.name, ptm)
        cmp1 = IPNetNSHost(cmp1_cfg.name, ptm)
        net = IPNetNSHost(net_cfg.name, ptm)

        root.configure_logging(debug=True)
        zoo1.configure_logging(debug=True)
        cmp1.configure_logging(debug=True)
        net.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)
        net.config_from_ptc_def(net_cfg, net_icfg)

        root.link_interface(root.interfaces['zoo1eth0'],
                            zoo1, zoo1.interfaces['eth0'])
        root.link_interface(root.interfaces['cmp1eth0'],
                            cmp1, cmp1.interfaces['eth0'])

        ptm_i.hosts_by_name['root'] = root
        ptm_i.hosts_by_name['zoo1'] = zoo1
        ptm_i.hosts_by_name['cmp1'] = cmp1
        ptm_i.hosts_by_name['net'] = net
        ptm_i.host_by_start_order.append([root])
        ptm_i.host_by_start_order.append([zoo1])
        ptm_i.host_by_start_order.append([cmp1])
        ptm_i.host_by_start_order.append([net])
        ptm_i.startup()

        self.assertTrue(LinuxCLI().cmd(
            'midonet-cli --midonet-url="' +
            version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url') +
            '" -A -e "host list"').ret_code == 0)

        ptm_i.shutdown()

        self.assertFalse(LinuxCLI().cmd(
            'midonet-cli --midonet-url="' +
            version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url') +
            '-A -e "hosts list"').ret_code == 0)

    def tearDown(self):
        pass
        LinuxCLI().cmd('ip netns del cmp1')
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip l del cmp1eth0')
        LinuxCLI().cmd('ip l del zoo1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')
        if LinuxCLI().exists('/var/run/zookeeper.1/pid'):
            pid = LinuxCLI().read_from_file('/var/run/zookeeper.1/pid')
            LinuxCLI().cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/midolman.1/pid'):
            pid = LinuxCLI().read_from_file('/var/run/midolman.1/pid')
            LinuxCLI().cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/midolman.1/dnsmasq.pid'):
            pid = LinuxCLI().read_from_file('/var/run/midolman.1/dnsmasq.pid')
            LinuxCLI().cmd('kill ' + str(pid))

run_unit_test(MidonetAPITest)
