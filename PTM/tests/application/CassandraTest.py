__author__ = 'micucci'

import unittest


class CassandraTest(unittest.TestCase):
    def test_startup(self):
        self.skipTest("Cassandra is not working on Jenkins currently")
        """
        lm = LogManager('./test-logs')
        ptm = HostPhysicalTopologyManagerImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../../..',
                                            log_manager=lm)

        root_cfg = HostDef('root',
                           bridges={'br0': BridgeDef('br0', ip_addresses=[IP('10.0.0.240')])},
                           interfaces={'cass1eth0': InterfaceDef('cass1eth0', linked_bridge='br0')})
        cass1_cfg = HostDef('cass1',
                           interfaces={'eth0': InterfaceDef('eth0', ip_addresses=[IP('10.0.0.5')])})

        cass1_icfg= ImplementationDef('cass1', 'PTM.host.IPNetNSHost',
                                      [ApplicationDef('PTM.application.Cassandra', id='1',
                                                       cassandra_ips=['10.0.0.5'], init_token="")])
        root_icfg = ImplementationDef('cass1', 'PTM.RootHost', [])

        root = RootHost('root', ptm)
        cass1 = IPNetNSHost(cass1_cfg.name, ptm)

        log = lm.add_file_logger('test.log', 'test')
        root.configure_logging(debug=True)
        cass1.configure_logging(debug=True)

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

        cass1.start_applications()

        pid = LinuxCLI().read_from_file('/run/cassandra.1/cassandra.pid').rstrip()
        self.assertTrue(LinuxCLI().is_pid_running(pid))

        cass1.stop_applications()

        time.sleep(1)
        self.assertFalse(LinuxCLI().is_pid_running(pid))

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
        """

from CBT.UnitTestRunner import run_unit_test
run_unit_test(CassandraTest)
