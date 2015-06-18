__author__ = 'micucci'

import unittest
import json
import time

from common.CLI import LinuxCLI
from PTM.CassandraHost import CassandraHost
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager, HOST_CONTROL_CMD_NAME
from PTM.PhysicalTopologyConfig import *


class CassandraHostTest(unittest.TestCase):
    def test_startup(self):
        ptm = PhysicalTopologyManager(root_dir='../..', log_root_dir='./tmp/logs')

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'cass1eth0': InterfaceDef('cass1eth0', linked_bridge='br0')})
        cass1_cfg = HostDef('cass1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.5')])})

        cass1_icfg= ImplementationDef('cass1', 'PTM.CassandraHost', id='1', cassandra_ips=['10.0.0.5'],
                                      init_token="")
        root_icfg = ImplementationDef('cass1', 'PTM.RootHost')

        root = RootHost('root', )
        cass1 = CassandraHost(cass1_cfg.name, )

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        cass1.config_from_ptc_def(cass1_cfg, cass1_icfg)

        root.link_interface(root.interfaces['cass1eth0'], cass1, cass1.interfaces['eth0'])

        ptm.hosts_by_name['root'] = root
        ptm.hosts_by_name['cass1'] = cass1
        ptm.host_by_start_order.append(root)
        ptm.host_by_start_order.append(cass1)

        root.create()
        cass1.create()

        root.boot()
        cass1.boot()

        root.net_up()
        cass1.net_up()

        root.net_finalize()
        cass1.net_finalize()

        cass1.prepare_config()

        start_process = ptm.unshare_control('start', cass1)
        stdout, stderr = start_process.communicate()
        start_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if start_process.returncode != 0:
            raise SubprocessFailedException('Host control start failed with: ' + str(start_process.returncode))
        cass1.wait_for_process_start()

        pid = LinuxCLI().read_from_file('/run/cassandra.1/cassandra.pid').rstrip()
        self.assertTrue(LinuxCLI().grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid))

        stop_process = ptm.unshare_control('stop', cass1)
        stdout, stderr = stop_process.communicate()
        stop_process.poll()
        print("Host control process output: ")
        print stdout
        print("Host control process error output: ")
        print stderr
        if stop_process.returncode != 0:
            raise SubprocessFailedException('Host control stop failed with: ' + str(stop_process.returncode))

        cass1.wait_for_process_stop()
        time.sleep(1)
        self.assertFalse(LinuxCLI().grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid))

        root.net_down()
        cass1.net_down()

        root.shutdown()
        cass1.shutdown()

        root.remove()
        cass1.remove()

    def tearDown(self):
        pass
        LinuxCLI().cmd('ip netns del cass1')
        LinuxCLI().cmd('ip l del cass1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')
        if LinuxCLI().exists('/var/run/cassandra.1/cassandra.pid'):
            pid = LinuxCLI().read_from_file('/var/run/cassandra.1/cassandra.pid')
            LinuxCLI().cmd('kill ' + str(pid))

if __name__ == '__main__':

    unittest.main()
