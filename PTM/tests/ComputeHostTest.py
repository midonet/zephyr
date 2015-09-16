__author__ = 'micucci'

import unittest
import json
import time
import datetime
import os
import logging

from common.CLI import LinuxCLI
from PTM.ComputeHost import ComputeHost
from PTM.CassandraHost import CassandraHost
from PTM.ZookeeperHost import ZookeeperHost
from PTM.RootHost import RootHost
from PTM.PhysicalTopologyManager import PhysicalTopologyManager, HOST_CONTROL_CMD_NAME
from PTM.PhysicalTopologyConfig import *
from PTM.Interface import Interface
from common.LogManager import LogManager


class ComputeHostTest(unittest.TestCase):
    def test_create_vm(self):
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)
        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'cmp1eth0': InterfaceDef('cmp1eth0', linked_bridge='br0')})
        cmp1_cfg = HostDef('cmp1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.8')])})

        cmp1_icfg= ImplementationDef('cmp1', 'PTM.ComputeHost', id='1')
        root_icfg = ImplementationDef('cmp1', 'PTM.RootHost')

        root = RootHost('root', ptm)
        cmp1 = ComputeHost(cmp1_cfg.name, ptm)

        log = lm.add_file_logger('test.log', 'test')
        root.set_logger(log)
        cmp1.set_logger(log)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)

        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        cmp1.create()

        cmp1.boot()

        root.net_up()
        cmp1.net_up()

        root.net_finalize()
        cmp1.net_finalize()

        vm1 = cmp1.create_vm("vm1")
        vm1.create_interface('eth0', ip_list=['10.1.1.2'])

        self.assertTrue('eth0' in vm1.interfaces)

        vm1.create()
        vm1.boot()
        vm1.net_up()
        vm1.net_finalize()

        self.assertTrue(LinuxCLI().grep_cmd('ip netns exec vm1 ip l', 'eth0'))

        vm1.net_down()
        vm1.shutdown()
        vm1.remove()

        cmp1.net_down()
        root.net_down()
        cmp1.shutdown()
        root.shutdown()
        cmp1.remove()

    def test_startup(self):
        lm = LogManager('./test-logs')
        ptm = PhysicalTopologyManager(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..', log_manager=lm)
        ptm.configure_logging(debug=True)
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

        zoo1_icfg= ImplementationDef('zoo1', 'PTM.ZookeeperHost', id='1',
                                     zookeeper_ips=['10.0.0.2'])
        #cass1_icfg= ImplementationDef('cass1', 'PTM.CassandraHost', id='1',
        #                             cassandra_ips=['10.0.0.5'],
        #                             init_token="")
        cmp1_icfg= ImplementationDef('cmp1', 'PTM.ComputeHost', id='1',
                                     zookeeper_ips=['10.0.0.2'],
                                     cassandra_ips=[])#['10.0.0.5'])
        root_icfg = ImplementationDef('root', 'PTM.RootHost')

        root = RootHost('root', ptm)
        zoo1 = ZookeeperHost(zoo1_cfg.name, ptm)
        #cass1 = CassandraHost(cass1_cfg.name, ptm)
        cmp1 = ComputeHost(cmp1_cfg.name, ptm)

        root.set_logger(lm.add_tee_logger('test.log', name='test-root', file_log_level=logging.DEBUG,
                                          stdout_log_level=logging.DEBUG))
        zoo1.set_logger(lm.add_tee_logger('test.log', name='test-zoo1', file_log_level=logging.DEBUG,
                                          stdout_log_level=logging.DEBUG))
        #cass1.set_logger(lm.add_tee_logger('test.log', name='test-cass1', file_log_level=logging.DEBUG,
        #                                   stdout_log_level=logging.DEBUG))
        cmp1.set_logger(lm.add_tee_logger('test.log', name='test-cmp1', file_log_level=logging.DEBUG,
                                          stdout_log_level=logging.DEBUG))

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)
        #cass1.config_from_ptc_def(cass1_cfg, cass1_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)

        root.link_interface(root.interfaces['zoo1eth0'], zoo1, zoo1.interfaces['eth0'])
        #root.link_interface(root.interfaces['cass1eth0'], cass1, cass1.interfaces['eth0'])
        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        ptm.hosts_by_name['root'] = root
        ptm.hosts_by_name['zoo1'] = zoo1
        #ptm.hosts_by_name['cass1'] = cass1
        ptm.hosts_by_name['cmp1'] = cmp1
        ptm.host_by_start_order.append(root)
        ptm.host_by_start_order.append(zoo1)
        #ptm.host_by_start_order.append(cass1)
        ptm.host_by_start_order.append(cmp1)

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
            h.wait_for_process_start()

        pid = LinuxCLI().read_from_file('/run/midolman.1/pid').rstrip()
        self.assertTrue(LinuxCLI(log_cmd=True).grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid))

        for h in ptm.host_by_start_order:
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

        deadline = datetime.datetime.now() + datetime.timedelta(seconds=5)
        while LinuxCLI(log_cmd=False).grep_cmd('ps -aef | sed -e "s/  */ /g" | cut -f 2 -d " "', pid):
            if datetime.datetime.now() > deadline:
                self.fail("MM process " + pid + " did not stop within timeout")

        for h in ptm.host_by_start_order:
            h.net_down()

        for h in ptm.host_by_start_order:
            h.shutdown()

        for h in ptm.host_by_start_order:
            h.remove()

    def tearDown(self):
        pass
        LinuxCLI().cmd('ip netns del cmp1')
        #LinuxCLI().cmd('ip netns del cass1')
        LinuxCLI().cmd('ip netns del zoo1')
        LinuxCLI().cmd('ip netns del vm1')
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
run_unit_test(ComputeHostTest)
