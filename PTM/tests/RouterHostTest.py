__author__ = 'micucci'

import unittest
import json
import time
import os

from common.CLI import LinuxCLI
from PTM.RouterHost import RouterHost
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager, HOST_CONTROL_CMD_NAME
from PTM.PhysicalTopologyConfig import *
from common.LogManager import LogManager

class RouterHostTest(unittest.TestCase):
    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'edge1eth0': InterfaceDef('edge1eth0', linked_bridge='br0')})
        edge1_cfg = HostDef('edge1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.2')])})

        edge1_icfg= ImplementationDef('edge1', 'PTM.RouterHost', id='1')
        root_icfg = ImplementationDef('edge1', 'PTM.RootHost')

        root = RootHost('root', ptm)
        edge1 = RouterHost(edge1_cfg.name, ptm)

        log = lm.add_file_logger('test.log', 'test')
        root.set_logger(log)
        edge1.set_logger(log)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        edge1.config_from_ptc_def(edge1_cfg, edge1_icfg)

        root.link_interface(root.interfaces['edge1eth0'], edge1, edge1.interfaces['eth0'])

        ptm.hosts_by_name['root'] = root
        ptm.hosts_by_name['edge1'] = edge1
        ptm.host_by_start_order.append(root)
        ptm.host_by_start_order.append(edge1)

        root.create()
        edge1.create()

        root.boot()
        edge1.boot()

        root.net_up()
        edge1.net_up()

        root.net_finalize()
        edge1.net_finalize()

        edge1.prepare_config()

        start_process = ptm.unshare_control('start', edge1)
        stdout, stderr = start_process.communicate()
        start_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if start_process.returncode != 0:
            raise SubprocessFailedException('Host control start failed with: ' + str(start_process.returncode))
        edge1.wait_for_process_start()

        bgpd_pid = LinuxCLI().read_from_file('/run/quagga.1/bgpd.pid').rstrip()
        zebra_pid = LinuxCLI().read_from_file('/run/quagga.1/zebra.pid').rstrip()
        self.assertTrue(bgpd_pid in LinuxCLI().get_running_pids())
        self.assertTrue(zebra_pid in LinuxCLI().get_running_pids())

        stop_process = ptm.unshare_control('stop', edge1)
        stdout, stderr = stop_process.communicate()
        stop_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if stop_process.returncode != 0:
            raise SubprocessFailedException('Host control start failed with: ' + str(stop_process.returncode))

        edge1.wait_for_process_stop()
        time.sleep(1)
        self.assertFalse(bgpd_pid in LinuxCLI().get_running_pids())

        root.net_down()
        edge1.net_down()

        root.shutdown()
        edge1.shutdown()

        root.remove()
        edge1.remove()

    def tearDown(self):
        LinuxCLI().cmd('ip netns del edge1')
        LinuxCLI().cmd('ip l del edge1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')
        if LinuxCLI().exists('/var/run/quagga.1/bgpd.pid'):
            pid = LinuxCLI().read_from_file('/var/run/quagga.1/bgpd.pid')
            LinuxCLI().cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/quagga.1/zebra.pid'):
            pid = LinuxCLI().read_from_file('/var/run/quagga.1/zebra.pid')
            LinuxCLI().cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/quagga.1/watchquagga.pid'):
            pid = LinuxCLI().read_from_file('/var/run/quagga.1/watchquagga.pid')
            LinuxCLI().cmd('kill ' + str(pid))

from CBT.UnitTestRunner import run_unit_test
run_unit_test(RouterHostTest)
