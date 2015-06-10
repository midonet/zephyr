__author__ = 'micucci'

import unittest

import time

from common.CLI import *
from common.Exceptions import *
from PTM.Host import Host
from PTM.VirtualInterface import VirtualInterface
from PTM.Interface import Interface


class VirtualInterfaceTest(unittest.TestCase):
    def test_create_no_peer(self):
        h = Host('test', LinuxCLI(), lambda n: None, lambda n: None)
        i = VirtualInterface(name='testi', host=h, ip_addr=['192.168.0.2'])

        i.create()  # should skip setting peer on host

        self.assertTrue(LinuxCLI().grep_cmd('ip l', 'testi'))
        self.assertTrue(LinuxCLI().grep_cmd('ip l', i.peer_name))

        i.up()  # should still work for near end device
        time.sleep(1)

        self.assertTrue(LinuxCLI().grep_cmd('ip l | grep testi', 'state UP'))

        i.down()
        time.sleep(1)

        self.assertFalse(LinuxCLI().grep_cmd('ip l | grep testi', 'state UP'))

        i.remove()

        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi'))

    def test_create_with_host(self):
        h = Host('test', LinuxCLI(), lambda n: None, lambda n: None)
        h2 = Host('test2', NetNSCLI('test2'), CREATENSCMD, REMOVENSCMD)

        h2.create()

        p = Interface(name='testp', host=h2, ip_addr=['10.0.0.1'])
        i = VirtualInterface(name='testi', host=h, ip_addr=['192.168.0.2'], far_interface=p)

        i.create()  # should create and set peer on far host

        self.assertTrue(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertTrue(LinuxCLI().grep_cmd('ip l', 'testi'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi.p'))

        i.config_addr()

        # the far iface should be controllable on its own just like any interface
        p.add_ip('192.168.1.2')
        p.up()

        self.assertTrue(h2.cli.grep_cmd('ip a | grep testp | grep inet | sed -e "s/^ *//" | cut -f 2 -d " "',
                                        '192.168.1.2'))

        i.remove()  # should remove both interfaces

        self.assertFalse(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi'))

        h2.remove()


    def tearDown(self):
        LinuxCLI().cmd('ip l del testi')
        LinuxCLI().cmd('ip netns del test2')

if __name__ == '__main__':
    unittest.main()
