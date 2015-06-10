__author__ = 'micucci'

import unittest


from PTM.ComputeHost import *
from PTM.RootHost import RootHost
from PTM.VMHost import VMHost
from common.IP import IP
from PTM.PhysicalTopologyConfig import *
from common.CLI import *
from PTM.Interface import Interface

class VMHostTest(unittest.TestCase):

    def setUp(self):
        self.hypervisor = None
        self.root_host = None

        root_hostcfg = HostDef('root',
                        interfaces={'hveth0': InterfaceDef('hveth0')})
        root_host_implcfg = ImplementationDef('test', 'RootHost')

        hypervisorcfg = HostDef('hv',
                        interfaces={'eth0': InterfaceDef('eth0', ['192.168.1.3'])})
        hypervisor_implcfg = ImplementationDef('test', 'ComputeHost')

        self.root_host = RootHost(root_hostcfg.name)
        self.hypervisor = ComputeHost(hypervisorcfg.name)

        # Now configure the host with the definition and impl configs
        self.root_host.config_from_ptc_def(root_hostcfg, root_host_implcfg)
        self.hypervisor.config_from_ptc_def(hypervisorcfg, hypervisor_implcfg)

        self.root_host.link_interface(self.root_host.interfaces['hveth0'],
                                      self.hypervisor, self.hypervisor.interfaces['eth0'])

        self.root_host.create()
        self.hypervisor.create()
        self.root_host.boot()
        self.hypervisor.boot()
        self.root_host.net_up()
        self.hypervisor.net_up()
        self.root_host.net_finalize()
        self.hypervisor.net_finalize()

    def test_create_vm(self):

        vm_host = self.hypervisor.create_vm('test_vm')
        self.assertIs(vm_host, self.hypervisor.get_vm('test_vm'))

        vm_host.create()
        vm_host.boot()
        vm_host.net_up()
        vm_host.net_finalize()

        vm_host.shutdown()
        vm_host.remove()

    def test_create_vm_interface(self):

        vm_host = self.hypervisor.create_vm('test_vm')
        self.assertIs(vm_host, self.hypervisor.get_vm('test_vm'))

        vm_host.create()
        vm_host.boot()
        vm_host.net_up()
        vm_host.net_finalize()

        new_if = vm_host.create_interface('eth0', ip_list=[IP('10.50.50.3')])

        self.assertTrue(vm_host.cli.grep_cmd('ip l', 'eth0'))
        self.assertTrue(self.hypervisor.cli.grep_cmd('ip l', 'test_vmeth0'))

        vm_host.shutdown()
        vm_host.remove()

    def tearDown(self):
        self.root_host.net_down()
        self.hypervisor.net_down()
        self.hypervisor.shutdown()
        self.root_host.shutdown()
        self.hypervisor.remove()
        self.root_host.remove()
        LinuxCLI().cmd('ip netns del test_vm')

if __name__ == '__main__':
    unittest.main()
