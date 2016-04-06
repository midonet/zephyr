# Copyright 2016 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from zephyr.common.tcp_sender import *
from zephyr.common.utils import run_unit_test


class TCPSenderTest(unittest.TestCase):
    def test_send_packet_default(self):
        cli = LinuxCLI(debug=True)

        self.assertRaises(ArgMismatchException,
                          TCPSender.send_packet, cli, 'eth0')

    def test_send_packet_arp(self):
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0', packet_type='arp',
            source_ip='1.1.1.1', dest_ip='2.2.2.2',
            packet_options={'command': 'request', 'sip': '1.1.1.1'}).command
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
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0',
            packet_type='ip', packet_options={'len': '30'}).command
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t ip "len=30"' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('-A' not in out)
        self.assertTrue('-B' not in out)
        self.assertTrue('arp' not in out)
        self.assertTrue('sum' not in out)

    def test_send_packet_bytes(self):
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0', packet_type=None,
            source_mac='rand', dest_mac='00:11:22:33:44:55',
            byte_data='deadbeef').command
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-a rand' in out)
        self.assertTrue('-b 00:11:22:33:44:55' in out)
        self.assertTrue('deadbeef' in out)
        self.assertTrue('-t' not in out)
        self.assertTrue('-A' not in out)
        self.assertTrue('-B' not in out)
        self.assertTrue('ip' not in out)

    def test_send_packet_real(self):
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0', packet_type='arp',
            source_ip='1.1.1.1', dest_ip='2.2.2.2',
            packet_options={'command': 'request', 'sip': '1.1.1.1'}).command
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t arp "request, sip=1.1.1.1"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('icmp' not in out)
        self.assertTrue('targetip' not in out)

    def test_send_packet_tcp_real(self):
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0', packet_type='tcp',
            source_ip='1.1.1.1', dest_ip='2.2.2.2',
            source_port=22, dest_port=80).command
        self.assertTrue('mz eth0' in out)
        self.assertTrue('"sp=22,dp=80"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('tcp' in out)

    def test_send_packet_and_receive_packet(self):
        cli = LinuxCLI(debug=True)
        out = TCPSender.send_packet(
            cli, interface='eth0', packet_type='arp',
            source_ip='1.1.1.1', dest_ip='2.2.2.2',
            packet_options={'command': 'request', 'sip': '1.1.1.1'}).command
        self.assertTrue('mz eth0' in out)
        self.assertTrue('-t arp "request, sip=1.1.1.1"' in out)
        self.assertTrue('-A 1.1.1.1' in out)
        self.assertTrue('-B 2.2.2.2' in out)
        self.assertTrue('-a' not in out)
        self.assertTrue('-b' not in out)
        self.assertTrue('icmp' not in out)
        self.assertTrue('targetip' not in out)

run_unit_test(TCPSenderTest)
