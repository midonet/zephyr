__author__ = 'micucci'

import unittest
import os
import time

from common.CLI import LinuxCLI
from PTM.host.RootHost import RootHost
from PTM.host.IPNetNSHost import IPNetNSHost
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.PhysicalTopologyConfig import *
from common.LogManager import LogManager


class MidolmanTest(unittest.TestCase):
    def test_create_vm(self):
        lm = LogManager('./test-logs')
        ptm_i = ConfiguredHostPTMImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../../..', log_manager=lm)
        ptm_i.configure_logging(debug=True)
        ptm = PhysicalTopologyManager(ptm_i)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'cmp1eth0': InterfaceDef('cmp1eth0', linked_bridge='br0')})
        cmp1_cfg = HostDef('cmp1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.8')])})

        cmp1_icfg= ImplementationDef('cmp1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.Midolman', id='1')])
        root_icfg = ImplementationDef('root', 'PTM.RootHost', [])

        root = RootHost('root', ptm)
        cmp1 = IPNetNSHost(cmp1_cfg.name, ptm)

        root.configure_logging(debug=True)
        cmp1.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)

        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        cmp1.cli.log_cmd = True

        root.create()
        cmp1.create()

        root.boot()
        cmp1.boot()

        root.net_up()
        cmp1.net_up()

        root.net_finalize()
        cmp1.net_finalize()

        mm_app = cmp1.applications[0]
        """ :type: Midolman"""
        vm1 = mm_app.create_vm("vm1")
        vm1.create_interface('eth0', ip_list=['10.1.1.2'])

        self.assertTrue('eth0' in vm1.interfaces)

        self.assertTrue(LinuxCLI().grep_cmd('ip netns exec vm1 ip l', 'eth0'))
        self.assertTrue(LinuxCLI().grep_cmd('ip netns exec cmp1 ip l', 'vm1eth0'))
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
        ptm_i = ConfiguredHostPTMImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../../..', log_manager=lm)
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

        zoo1_icfg= ImplementationDef('zoo1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.Zookeeper', id='1',
                                                     zookeeper_ips=['10.0.0.2'])])
        cmp1_icfg= ImplementationDef('cmp1', 'PTM.host.IPNetNSHost',
                                     [ApplicationDef('PTM.application.Midolman', id='1',
                                                     zookeeper_ips=['10.0.0.2'], cassandra_ips=[])])
        root_icfg = ImplementationDef('root', 'PTM.RootHost', [])

        root = RootHost('root', ptm)
        zoo1 = IPNetNSHost(zoo1_cfg.name, ptm)
        cmp1 = IPNetNSHost(cmp1_cfg.name, ptm)

        root.configure_logging(debug=True)
        zoo1.configure_logging(debug=True)
        cmp1.configure_logging(debug=True)

        # Now configure the host with the definition and impl configs
        root.config_from_ptc_def(root_cfg, root_icfg)
        zoo1.config_from_ptc_def(zoo1_cfg, zoo1_icfg)
        cmp1.config_from_ptc_def(cmp1_cfg, cmp1_icfg)

        root.link_interface(root.interfaces['zoo1eth0'], zoo1, zoo1.interfaces['eth0'])
        root.link_interface(root.interfaces['cmp1eth0'], cmp1, cmp1.interfaces['eth0'])

        ptm_i.hosts_by_name['root'] = root
        ptm_i.hosts_by_name['zoo1'] = zoo1
        ptm_i.hosts_by_name['cmp1'] = cmp1
        ptm_i.host_by_start_order.append([root])
        ptm_i.host_by_start_order.append([zoo1])
        ptm_i.host_by_start_order.append([cmp1])
        ptm_i.startup()

        timeout = time.time() + 10
        while not LinuxCLI().exists('/run/midolman.1/pid'):
            if time.time() > timeout:
                self.fail('Midolman PID file not created within timeout')
            time.sleep(1)

        pid = LinuxCLI().read_from_file('/run/midolman.1/pid').rstrip()
        print "PID = " + pid
        print "PS = " + LinuxCLI().cmd("ps -aef").stdout

        self.assertTrue(LinuxCLI().is_pid_running(pid))

        ptm_i.shutdown()

        print LinuxCLI().cmd('ip netns').stdout

    def tearDown(self):
        pass
        LinuxCLI(log_cmd=True).cmd('ip netns del cmp1')
        LinuxCLI(log_cmd=True).cmd('ip netns del zoo1')
        LinuxCLI(log_cmd=True).cmd('ip netns del vm1')
        LinuxCLI(log_cmd=True).cmd('ip l del cmp1eth0')
        LinuxCLI(log_cmd=True).cmd('ip l del zoo1eth0')
        LinuxCLI(log_cmd=True).cmd('ip l set br0 down')
        LinuxCLI(log_cmd=True).cmd('brctl delbr br0')
        if LinuxCLI().exists('/var/run/zookeeper.1/pid'):
            pid = LinuxCLI().read_from_file('/var/run/zookeeper.1/pid')
            LinuxCLI(log_cmd=True).cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/midolman.1/pid'):
            pid = LinuxCLI().read_from_file('/var/run/midolman.1/pid')
            LinuxCLI(log_cmd=True).cmd('kill ' + str(pid))
        if LinuxCLI().exists('/var/run/midolman.1/dnsmasq.pid'):
            pid = LinuxCLI().read_from_file('/var/run/midolman.1/dnsmasq.pid')
            LinuxCLI(log_cmd=True).cmd('kill ' + str(pid))

from CBT.UnitTestRunner import run_unit_test
run_unit_test(MidolmanTest)
