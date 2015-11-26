__author__ = 'micucci'

import unittest
import time
import os

from common.CLI import LinuxCLI
from PTM.application.Midolman import Midolman
from PTM.application.Zookeeper import Zookeeper
from PTM.application.MidonetAPI import MidonetAPI
from PTM.host.RootHost import RootHost
from PTM.host.IPNetNSHost import IPNetNSHost
from PTM.HostPhysicalTopologyManagerImpl import HostPhysicalTopologyManagerImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from PTM.PhysicalTopologyConfig import *
from common.LogManager import LogManager
import CBT.VersionConfig as version_config


class MidonetAPITest(unittest.TestCase):
    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm_i = HostPhysicalTopologyManagerImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../../..',
                                                  log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'zoo1eth0': InterfaceDef('zoo1eth0', linked_bridge='br0'),
                                       'cmp1eth0': InterfaceDef('cmp1eth0', linked_bridge='br0')})
        zoo1_cfg = HostDef('zoo1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.2')])})
        cmp1_cfg = HostDef('cmp1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.8')])})
        net_cfg = HostDef('net')

        zoo1_icfg= ImplementationDef('zoo1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.Zookeeper', id='1',
                                                     zookeeper_ips=['10.0.0.2'])])
        cmp1_icfg= ImplementationDef('cmp1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.Midolman', id='1',
                                                     zookeeper_ips=['10.0.0.2'], cassandra_ips=[])])
        root_icfg = ImplementationDef('root', 'PTM.host.RootHost', [])
        net_icfg = ImplementationDef('net1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.MidonetAPI',
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

        root.link_interface(root.interfaces['zoo1eth0'], zoo1, zoo1.interfaces['eth0'])
        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        ptm_i.hosts_by_name['root'] = root
        ptm_i.hosts_by_name['zoo1'] = zoo1
        ptm_i.hosts_by_name['cmp1'] = cmp1
        ptm_i.hosts_by_name['net'] = net
        ptm_i.host_by_start_order.append(root)
        ptm_i.host_by_start_order.append(zoo1)
        ptm_i.host_by_start_order.append(cmp1)
        ptm_i.host_by_start_order.append(net)

        for h in ptm_i.host_by_start_order:
            h.create()

        for h in ptm_i.host_by_start_order:
            h.boot()

        for h in ptm_i.host_by_start_order:
            h.net_up()

        for h in ptm_i.host_by_start_order:
            h.net_finalize()

        for h in ptm_i.host_by_start_order:
            h.prepare_applications(lm)

        for h in ptm_i.host_by_start_order:
            h.start_applications()

        self.assertTrue(LinuxCLI().cmd('midonet-cli --midonet-url="' +
                                       version_config.ConfigMap.get_configured_parameter('param_midonet_api_url') +
                                       '" -A -e "host list"').ret_code == 0)

        for h in reversed(ptm_i.host_by_start_order):
            h.stop_applications()

        time.sleep(1)
        self.assertFalse(LinuxCLI().cmd('midonet-cli '
                                        '--midonet-url="http://localhost:8080/midonet-api/" '
                                        '-A -e "hosts list"').ret_code == 0)

        for h in reversed(ptm_i.host_by_start_order):
            h.net_down()

        for h in reversed(ptm_i.host_by_start_order):
            h.shutdown()

        for h in reversed(ptm_i.host_by_start_order):
            h.remove()

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

from CBT.UnitTestRunner import run_unit_test
run_unit_test(MidonetAPITest)
