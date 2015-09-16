__author__ = 'micucci'

import unittest
import json
import time
import os

from common.CLI import LinuxCLI
from PTM.ComputeHost import ComputeHost
from PTM.CassandraHost import CassandraHost
from PTM.ZookeeperHost import ZookeeperHost
from PTM.NetworkHost import NetworkHost
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager, HOST_CONTROL_CMD_NAME
from PTM.PhysicalTopologyConfig import *
from common.LogManager import LogManager

import CBT.VersionConfig as version_config

class NetworkHostTest(unittest.TestCase):
    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'zoo1eth0': InterfaceDef('zoo1eth0', linked_bridge='br0'),
                                       #'cass1eth0': InterfaceDef('cass1eth0', linked_bridge='br0'),
                                       'cmp1eth0': InterfaceDef('cmp1eth0', linked_bridge='br0')})
        zoo1_cfg = HostDef('zoo1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.2')])})
        #cass1_cfg = HostDef('cass1',
        #                    interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.5')])})
        cmp1_cfg = HostDef('cmp1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.8')])})
        net_cfg = HostDef('net')

        zoo1_icfg= ImplementationDef('zoo1', 'PTM.ZookeeperHost', id='1',
                                     zookeeper_ips=['10.0.0.2'])
        #cass1_icfg= ImplementationDef('cass1', 'PTM.CassandraHost', id='1',
        #                              cassandra_ips=['10.0.0.5'],
        #                              init_token="56713727820156410577229101238628035242")
        cmp1_icfg= ImplementationDef('cmp1', 'PTM.ComputeHost', id='1',
                                     zookeeper_ips=['10.0.0.2'],
                                     cassandra_ips=[])#['10.0.0.5'])
        root_icfg = ImplementationDef('cmp1', 'PTM.RootHost')
        net_icfg = ImplementationDef('cmp1', 'PTM.NetworkHost',
                                     zookeeper_ips=['10.0.0.2'])

        root = RootHost('root', ptm)
        zoo1 = ZookeeperHost(zoo1_cfg.name, ptm)
        #cass1 = CassandraHost(cass1_cfg.name, ptm)
        cmp1 = ComputeHost(cmp1_cfg.name, ptm)
        net = NetworkHost(net_cfg.name, ptm)

        log = lm.add_file_logger('test.log', 'test')
        root.set_logger(log)
        zoo1.set_logger(log)
        #cass1.set_logger(log)
        cmp1.set_logger(log)
        net.set_logger(log)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)
        #cass1.config_from_ptc_def(cass1_cfg, cass1_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)
        net.config_from_ptc_def(net_cfg, net_icfg)

        root.link_interface(root.interfaces['zoo1eth0'], zoo1, zoo1.interfaces['eth0'])
        #root.link_interface(root.interfaces['cass1eth0'], cass1, cass1.interfaces['eth0'])
        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        ptm.hosts_by_name['root'] = root
        ptm.hosts_by_name['zoo1'] = zoo1
        #ptm.hosts_by_name['cass1'] = cass1
        ptm.hosts_by_name['cmp1'] = cmp1
        ptm.hosts_by_name['net'] = net
        ptm.host_by_start_order.append(root)
        ptm.host_by_start_order.append(zoo1)
        #ptm.host_by_start_order.append(cass1)
        ptm.host_by_start_order.append(cmp1)
        ptm.host_by_start_order.append(net)

        for h in ptm.host_by_start_order:
            h.create()

        for h in ptm.host_by_start_order:
            h.boot()

        for h in ptm.host_by_start_order:
            h.net_up()

        for h in ptm.host_by_start_order:
            h.net_finalize()

        for h in ptm.host_by_start_order:
            h.prepare_config()

        for h in ptm.host_by_start_order:
            start_process = ptm.unshare_control('start', h)

            stdout, stderr = start_process.communicate()
            start_process.poll()
            print("Host control process output: ")
            print stdout
            print("Host control process error output: ")
            print stderr
            if start_process.returncode != 0:
                raise SubprocessFailedException('Host control start failed with: ' + str(start_process.returncode))

            try:
                h.wait_for_process_start()
            except SubprocessFailedException:
                raw_input("Press Enter to continue...")

        self.assertTrue(LinuxCLI().cmd('midonet-cli --midonet-url="' + version_config.param_midonet_api_url +
                                       '" -A -e "host list"', return_status=True) == 0)


        for h in reversed(ptm.host_by_start_order):
            stop_process = ptm.unshare_control('stop', h)
            stdout, stderr = stop_process.communicate()
            stop_process.poll()
            print("Host control process output: ")
            print stdout
            print("Host control process error output: ")
            print stderr
            if stop_process.returncode != 0:
                raise SubprocessFailedException('Host control stop failed with: ' + str(stop_process.returncode))

            h.wait_for_process_stop()

        time.sleep(1)
        self.assertFalse(LinuxCLI().cmd('midonet-cli '
                                        '--midonet-url="http://localhost:8080/midonet-api/" '
                                        '-A -e "hosts list"',
                                        return_status=True) == 0)

        for h in reversed(ptm.host_by_start_order):
            h.net_down()

        for h in reversed(ptm.host_by_start_order):
            h.shutdown()

        for h in reversed(ptm.host_by_start_order):
            h.remove()

    def tearDown(self):
        pass
        LinuxCLI().cmd('ip netns del cmp1')
        #LinuxCLI().cmd('ip netns del cass1')
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip l del cmp1eth0')
        #LinuxCLI().cmd('ip l del cass1eth0')
        LinuxCLI().cmd('ip l del zoo1eth0')
        LinuxCLI().cmd('ip l set br0 down')
        LinuxCLI().cmd('brctl delbr br0')
        #if LinuxCLI().exists('/var/run/cassandra.1/cassandra.pid'):
        #    pid = LinuxCLI().read_from_file('/var/run/cassandra.1/cassandra.pid')
        #    LinuxCLI().cmd('kill ' + str(pid))
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
run_unit_test(NetworkHostTest)
