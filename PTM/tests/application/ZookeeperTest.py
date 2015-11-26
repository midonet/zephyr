__author__ = 'micucci'

import unittest
import time
import os

from common.CLI import LinuxCLI
from PTM.application.Zookeeper import Zookeeper
from PTM.host.RootHost import RootHost
from PTM.host.IPNetNSHost import IPNetNSHost
from PTM.HostPhysicalTopologyManagerImpl import HostPhysicalTopologyManagerImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from PTM.PhysicalTopologyConfig import *
from common.LogManager import LogManager


class ZookeeperTest(unittest.TestCase):
    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm_i = HostPhysicalTopologyManagerImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../../..',
                                                log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'zoo1eth0': InterfaceDef('zoo1eth0', linked_bridge='br0')})
        zoo1_cfg = HostDef('zoo1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.2')])})

        zoo1_icfg = ImplementationDef('zoo1', 'PTM.host.IPNetNSHost',
                                      [ApplicationDef('PTM.application.Zookeeper', id='1',
                                                      zookeeper_ips=['10.0.0.2'])])
        root_icfg = ImplementationDef('zoo1', 'PTM.host.RootHost', [])

        root = RootHost('root', ptm)
        zoo_host1 = IPNetNSHost('zoo1', ptm)

        root.configure_logging(debug=True)
        zoo_host1.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo_host1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)

        root.link_interface(root.interfaces['zoo1eth0'], zoo_host1, zoo_host1.interfaces['eth0'])

        ptm_i.hosts_by_name['root'] = root
        ptm_i.hosts_by_name['zoo1'] = zoo_host1
        ptm_i.host_by_start_order.append(root)
        ptm_i.host_by_start_order.append(zoo_host1)

        try:
            root.create()
            zoo_host1.create()

            root.boot()
            zoo_host1.boot()

            root.net_up()
            zoo_host1.net_up()

            root.net_finalize()
            zoo_host1.net_finalize()

            zoo_host1.start_applications()

            self.assertEqual('imok', zoo_host1.cli.cmd_pipe([['echo', 'ruok'], ['nc', 'localhost', '2181']]).stdout)

            timeout = time.time() + 30
            while not LinuxCLI().exists('/run/zookeeper.1/pid'):
                if time.time() > timeout:
                    self.fail("Zookeeper didn't start!")
                time.sleep(1)

            pid = LinuxCLI().read_from_file('/run/zookeeper.1/pid').rstrip()
            self.assertTrue(LinuxCLI().is_pid_running(pid))

            zoo_host1.stop_applications()

            time.sleep(1)
            self.assertFalse(LinuxCLI().is_pid_running(pid))
        finally:
            if LinuxCLI().exists('/run/zookeeper.1/pid'):
                zoo_host1.stop_applications()

            root.net_down()
            zoo_host1.net_down()

            root.shutdown()
            zoo_host1.shutdown()

            root.remove()
            zoo_host1.remove()

    def tearDown(self):
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip l del zoo1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(ZookeeperTest)
