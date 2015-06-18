__author__ = 'micucci'

import unittest
import json
import time

from common.CLI import LinuxCLI
from PTM.ZookeeperHost import ZookeeperHost
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager, HOST_CONTROL_CMD_NAME
from PTM.PhysicalTopologyConfig import *


class ZookeeperTest(unittest.TestCase):
    def test_startup(self):
        ptm = PhysicalTopologyManager(root_dir='../..', log_root_dir='./tmp/logs')

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'zoo1eth0': InterfaceDef('zoo1eth0', linked_bridge='br0')})
        zoo1_cfg = HostDef('zoo1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.2')])})

        zoo1_icfg= ImplementationDef('zoo1', 'PTM.ZookeeperHost', id='1', zookeeper_ips=['10.0.0.2'])
        root_icfg = ImplementationDef('zoo1', 'PTM.RootHost')

        root = RootHost('root', )
        zoo1 = ZookeeperHost(zoo1_cfg.name, )

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)

        root.link_interface(root.interfaces['zoo1eth0'], zoo1, zoo1.interfaces['eth0'])

        ptm.hosts_by_name['root'] = root
        ptm.hosts_by_name['zoo1'] = zoo1
        ptm.host_by_start_order.append(root)
        ptm.host_by_start_order.append(zoo1)

        root.create()
        zoo1.create()

        root.boot()
        zoo1.boot()

        root.net_up()
        zoo1.net_up()

        root.net_finalize()
        zoo1.net_finalize()

        zoo1.prepare_config()

        start_process = ptm.unshare_control('start', zoo1)
        stdout, stderr = start_process.communicate()
        start_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if start_process.returncode != 0:
            raise SubprocessFailedException('Host control start failed with: ' + str(start_process.returncode))
        zoo1.wait_for_process_start()

        pid = LinuxCLI().read_from_file('/run/zookeeper.1/pid').rstrip()
        self.assertTrue(LinuxCLI().grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid))

        stop_process = ptm.unshare_control('stop', zoo1)
        stdout, stderr = stop_process.communicate()
        stop_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if stop_process.returncode != 0:
            raise SubprocessFailedException('Host control start failed with: ' + str(stop_process.returncode))

        zoo1.wait_for_process_stop()
        time.sleep(1)
        self.assertFalse(LinuxCLI().grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid))

        root.net_down()
        zoo1.net_down()

        root.shutdown()
        zoo1.shutdown()

        root.remove()
        zoo1.remove()

    def tearDown(self):
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip l del zoo1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')

if __name__ == '__main__':
    unittest.main()
