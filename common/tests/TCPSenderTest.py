__author__ = 'vagrant'

import unittest
from common.CLI import LinuxCLI
from common.TCPSender import *

class TCPSenderTest(unittest.TestCase):
    def test_send_packet_default(self):
        cli = LinuxCLI(debug=True)

        self.assertRaises(ArgMismatchException, TCPSender.send_packet, cli, 'eth0')

    def test_send_packet_arp(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type='arp',
                              source_ip='1.1.1.1', dest_ip='2.2.2.2',
                              packet_cmd='request', packet_options={'sip': '1.1.1.1'})
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t arp "request, sip=1.1.1.1"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('icmp' not in out)
        self.assertTrue('targetip' not in out)

    def test_send_packet_arp_no_cmd(self):
        cli = LinuxCLI(debug=True)
        self.assertRaises(ArgMismatchException, TCPSender.send_packet,
                          cli, interface='eth0', packet_type='arp',
                          source_ip='1.1.1.1', dest_ip='2.2.2.2',
                          packet_options={'sip': '1.1.1.1'})

    def test_send_packet_ip(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type='ip', packet_options={'len': '30'})
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t ip "len=30"' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('-A' not in out)
        self.assertTrue('-B' not in out)
        self.assertTrue('arp' not in out)
        self.assertTrue('sum' not in out)

    def test_send_packet_bytes(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type=None,
                                    source_mac='rand', dest_mac='00:11:22:33:44:55',
                                    byte_data='deadbeef')
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-a rand' in out)
        self.assertTrue('-b 00:11:22:33:44:55' in out)
        self.assertTrue('deadbeef' in out)
        self.assertTrue('-t' not in out)
        self.assertTrue('-A' not in out)
        self.assertTrue('-B' not in out)
        self.assertTrue('ip' not in out)

    def test_send_packet_real(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type='arp',
                                    source_ip='1.1.1.1', dest_ip='2.2.2.2',
                                    packet_cmd='request', packet_options={'sip': '1.1.1.1'})
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t arp "request, sip=1.1.1.1"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('icmp' not in out)
        self.assertTrue('targetip' not in out)

    def test_send_packet_tcp_real(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type='tcp',
                                    source_ip='1.1.1.1', dest_ip='2.2.2.2',
                                    source_port=22, dest_port=80)
        self.assertTrue('mz eth0' in out)
        self.assertTrue('"sp=22,dp=80"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('tcp' in out)

    def test_send_packet_and_receive_packet(self):
        cli = LinuxCLI(debug=True, print_cmd=True)
        out = TCPSender.send_packet(cli, interface='eth0', packet_type='arp',
                                    source_ip='1.1.1.1', dest_ip='2.2.2.2',
                              packet_cmd='request', packet_options={'sip': '1.1.1.1'})
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t arp "request, sip=1.1.1.1"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('icmp' not in out)
        self.assertTrue('targetip' not in out)


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(TCPSenderTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

