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
from zephyr.common import pcap_packet
from zephyr.common.utils import run_unit_test


class PCAPPacketTest(unittest.TestCase):

    def test_char8_to_int16(self):
        self.assertEqual(
            0x09DA, pcap_packet.PCAPPacket.char8_to_int16(0x09, 0xDA))
        self.assertEqual(
            0, pcap_packet.PCAPPacket.char8_to_int16(0x00, 0x00))
        self.assertEqual(
            65535, pcap_packet.PCAPPacket.char8_to_int16(0xFF, 0xFF))
        self.assertEqual(
            65535, pcap_packet.PCAPPacket.char8_to_int16(255, 255))

    def test_char8_to_int32(self):
        self.assertEqual(
            0x09DAE203,
            pcap_packet.PCAPPacket.char8_to_int32(0x09, 0xDA, 0xE2, 0x03))
        self.assertEqual(
            0,
            pcap_packet.PCAPPacket.char8_to_int32(0x00, 0x00, 0x00, 0x00))
        self.assertEqual(
            65535,
            pcap_packet.PCAPPacket.char8_to_int32(0x00, 0x00, 0xFF, 0xFF))

    def test_char8_to_ip4(self):
        self.assertEqual(
            '10.0.2.2',
            pcap_packet.PCAPPacket.char8_to_ip4(0x0a, 0, 0x02, 0x02))
        self.assertEqual(
            '10.0.2.2',
            pcap_packet.PCAPPacket.char8_to_ip4(10, 0, 2, 2))
        self.assertEqual(
            '255.255.255.255',
            pcap_packet.PCAPPacket.char8_to_ip4(0xFF, 0xFF, 0xFF, 0xFF))

    def test_char8_to_mac_address(self):
        self.assertEqual(
            '0a:db:0a:db:0a:db',
            pcap_packet.PCAPPacket.char8_to_mac_address(
                0x0A, 0xDB, 0x0A, 0xdb, 0x0a, 0xdb))
        self.assertEqual(
            '00:00:00:00:00:00',
            pcap_packet.PCAPPacket.char8_to_mac_address(
                0, 0, 0, 0, 0, 0))
        self.assertEqual(
            'ff:ff:ff:ff:ff:ff',
            pcap_packet.PCAPPacket.char8_to_mac_address(
                255, 255, 255, 255, 255, 255))

    def test_cooked_packet_decoding(self):
        cooked_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0xDE, 0xAD, 0xBE, 0xEF]

        packet = pcap_packet.PCAPSLL()
        new_data = packet.parse_layer(cooked_packet_data)

        self.assertEqual(
            '08:00:27:c6:25:01', packet.source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', packet.dest_mac)
        self.assertEqual(
            [0xDE, 0xAD, 0xBE, 0xEF], new_data)

    def test_ethernet_ii_packet_decoding(self):
        eii_packet_data = \
            [0x52, 0x54, 0x00, 0x12, 0x35, 0x02, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x08, 0x00, 0xDE, 0xAD,
             0xBE, 0xEF]

        packet = pcap_packet.PCAPEthernet()
        new_data = packet.parse_layer(eii_packet_data)

        self.assertEqual(
            '08:00:27:c6:25:01', packet.source_mac)
        self.assertEqual(
            '52:54:00:12:35:02', packet.dest_mac)
        self.assertEqual(
            [0xDE, 0xAD, 0xBE, 0xEF], new_data)

    def test_ip4_packet_decoding(self):
        ip_data = \
            [0x45, 0x10, 0x00, 0x5c, 0x93, 0x06, 0x40, 0x00,
             0x40, 0x06, 0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f,
             0x0a, 0x00, 0x02, 0x02, 0xDE, 0xAD, 0xBE, 0xEF]

        ip_packet = pcap_packet.PCAPIP4()
        new_data = ip_packet.parse_layer(ip_data)

        self.assertEqual(
            '10.0.2.15', ip_packet.source_ip)
        self.assertEqual(
            '10.0.2.2', ip_packet.dest_ip)
        self.assertEqual(
            5, ip_packet.header_length)
        self.assertEqual(
            4, ip_packet.version)
        self.assertEqual(
            pcap_packet.IP4_PROTOCOL_TCP, ip_packet.protocol)
        self.assertEqual(
            pcap_packet.PCAPTCP, ip_packet.next_parse_recommendation)
        self.assertEqual(
            [0xDE, 0xAD, 0xBE, 0xEF], new_data)

    def test_TCP_packet_decoding(self):
        tcp_packet_data = \
            [0x00, 0x16, 0xd1, 0xf4, 0x52, 0x1a, 0x58, 0x7c,
             0x58, 0x25, 0x2e, 0x9b, 0x50, 0x18, 0x9f, 0xb0,
             0x18, 0x5f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20,
             0xb0, 0x2c, 0x08, 0xab, 0x7f, 0x98, 0x3c, 0x58,
             0x54, 0xeb, 0xde, 0x01, 0xd1, 0xc7, 0xbe, 0xf8,
             0x85, 0xba, 0xe4, 0xb6, 0xea, 0x06, 0x98, 0xf9,
             0xc0, 0xd2, 0xac, 0x17, 0x19, 0x85, 0x54, 0xdb,
             0xe1, 0x3b, 0x3e, 0x85, 0x61, 0xee, 0x31, 0xaf,
             0x36, 0xa6, 0x04, 0xd3, 0x51, 0x21, 0x09, 0x20]

        packet = pcap_packet.PCAPTCP()
        packet.parse_layer(tcp_packet_data)

        self.assertEqual(
            22, packet.source_port)
        self.assertEqual(
            53748, packet.dest_port)
        self.assertEqual(
            1377458300, packet.seq)
        self.assertEqual(
            1478831771, packet.ack)
        self.assertEqual(
            5, packet.data_offset)
        self.assertEqual(
            True, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ACK))
        self.assertEqual(
            True, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_PUSH))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_CWS))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ECE))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_FINAL))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_RESET))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_NS))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_SYN))
        self.assertEqual(
            False, packet.is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_URGENT))
        self.assertEqual(
            40880, packet.window_size)
        self.assertEqual(
            None, packet.next_parse_recommendation)

    def test_udp_packet_decoding(self):
        udp_packet_data = \
            [0x00, 0x16, 0x00, 0x1c, 0x00, 0x0c, 0x00, 0x00,
             0xDE, 0xAD, 0xBE, 0xEF]

        packet = pcap_packet.PCAPUDP()
        new_data = packet.parse_layer(udp_packet_data)

        self.assertEqual(
            22, packet.source_port)
        self.assertEqual(
            28, packet.dest_port)
        self.assertEqual(
            12, packet.length)
        self.assertEqual(
            0xDEADBEEF, pcap_packet.PCAPPacket.char8_to_int32(*new_data[0:4]))

        self.assertEqual(
            None, packet.next_parse_recommendation)

    def test_icmp_packet_decoding(self):
        icmp_packet_data = \
            [0x08, 0x00, 0xb7, 0x82, 0x1b, 0x9c, 0x00, 0x0c,
             0x1c, 0xe0, 0x3d, 0x55, 0x00, 0x00, 0x00, 0x00,
             0x07, 0xcd, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
             0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
             0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
             0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
             0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
             0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]

        packet = pcap_packet.PCAPICMP()
        packet.parse_layer(icmp_packet_data)

        self.assertEqual(
            pcap_packet.ICMP_PROTOCOL_TYPE_ECHO_REQUEST, packet.type)
        self.assertEqual(
            0, packet.code)
        self.assertEqual(
            [0x1b, 0x9c, 0x00, 0x0c], packet.header_data)

        self.assertEqual(
            None, packet.next_parse_recommendation)

    def test_arp_packet_decoding(self):
        arp_packet_data = \
            [0x00, 0x01, 0x08, 0x00, 0x06, 0x04, 0x00, 0x01,
             0x08, 0x00, 0x27, 0x7a, 0x9d, 0xff, 0xc0, 0xa8,
             0x01, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
             0xc0, 0xa8, 0x01, 0x01]

        packet = pcap_packet.PCAPARP()
        new_data = packet.parse_layer(arp_packet_data)

        self.assertEqual(
            pcap_packet.ARP_PROTOCOL_HW_TYPE_EHTERNET, packet.hw_type)
        self.assertEqual(
            pcap_packet.ETHERNET_PROTOCOL_TYPE_IP4, packet.proto_type)
        self.assertEqual(
            pcap_packet.ARP_PROTOCOL_OPERATION_REQUEST, packet.operation)
        self.assertEqual(
            6, packet.hw_addr_length)
        self.assertEqual(
            4, packet.proto_addr_length)
        self.assertEqual(
            [0x08, 0x00, 0x27, 0x7a, 0x9d, 0xff], packet.sender_hw_addr_raw)
        self.assertEqual(
            '08:00:27:7a:9d:ff', packet.sender_hw_addr_ether)
        self.assertEqual(
            [0xc0, 0xa8, 0x01, 0x0a], packet.sender_proto_addr_raw)
        self.assertEqual(
            '192.168.1.10', packet.sender_ip_addr)
        self.assertEqual(
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00], packet.target_hw_addr_raw)
        self.assertEqual(
            '00:00:00:00:00:00', packet.target_hw_addr_ether)
        self.assertEqual(
            [0xc0, 0xa8, 0x01, 0x01], packet.target_proto_addr_raw)
        self.assertEqual(
            '192.168.1.1', packet.target_ip_addr)
        self.assertEqual(
            0, len(new_data))

        self.assertEqual(None, packet.next_parse_recommendation)

    def test_ethernet_arp_packet_decoding(self):
        arp_packet_data = \
            [0x52, 0x54, 0x00, 0x12, 0x35, 0x02, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x08, 0x06, 0x00, 0x01,
             0x08, 0x00, 0x06, 0x04, 0x00, 0x01, 0x08, 0x00,
             0x27, 0x7a, 0x9d, 0xff, 0xc0, 0xa8, 0x01, 0x0a,
             0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0xa8,
             0x01, 0x01]

        packet = pcap_packet.PCAPEthernet()
        new_data = packet.parse_layer(arp_packet_data)

        self.assertEqual(pcap_packet.PCAPARP, packet.next_parse_recommendation)
        arp_packet = packet.next_parse_recommendation()
        new_data2 = arp_packet.parse_layer(new_data)

        self.assertEqual(
            pcap_packet.ARP_PROTOCOL_HW_TYPE_EHTERNET, arp_packet.hw_type)
        self.assertEqual(
            pcap_packet.ETHERNET_PROTOCOL_TYPE_IP4, arp_packet.proto_type)
        self.assertEqual(
            pcap_packet.ARP_PROTOCOL_OPERATION_REQUEST, arp_packet.operation)
        self.assertEqual(
            6, arp_packet.hw_addr_length)
        self.assertEqual(
            4, arp_packet.proto_addr_length)
        self.assertEqual(
            [0x08, 0x00, 0x27, 0x7a, 0x9d, 0xff],
            arp_packet.sender_hw_addr_raw)
        self.assertEqual(
            '08:00:27:7a:9d:ff', arp_packet.sender_hw_addr_ether)
        self.assertEqual(
            [0xc0, 0xa8, 0x01, 0x0a], arp_packet.sender_proto_addr_raw)
        self.assertEqual(
            '192.168.1.10', arp_packet.sender_ip_addr)
        self.assertEqual(
            [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            arp_packet.target_hw_addr_raw)
        self.assertEqual(
            '00:00:00:00:00:00', arp_packet.target_hw_addr_ether)
        self.assertEqual(
            [0xc0, 0xa8, 0x01, 0x01], arp_packet.target_proto_addr_raw)
        self.assertEqual(
            '192.168.1.1', arp_packet.target_ip_addr)
        self.assertEqual(
            0, len(new_data2))

        self.assertEqual(None, arp_packet.next_parse_recommendation)

    def test_full_packet_parsing_default_stack(self):
        full_eii_packet_data = \
            [0x52, 0x54, 0x00, 0x12, 0x35, 0x02, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x08, 0x00, 0x45, 0x10,
             0x00, 0x5c, 0x93, 0x06, 0x40, 0x00, 0x40, 0x06,
             0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f, 0x0a, 0x00,
             0x02, 0x02, 0x00, 0x16, 0xd1, 0xf4, 0x52, 0x1a,
             0x58, 0x7c, 0x58, 0x25, 0x2e, 0x9b, 0x50, 0x18,
             0x9f, 0xb0, 0x18, 0x5f, 0x00, 0x00, 0x00, 0x00,
             0x00, 0x20, 0xb0, 0x2c, 0x08, 0xab, 0x7f, 0x98,
             0x3c, 0x58, 0x54, 0xeb, 0xde, 0x01, 0xd1, 0xc7,
             0xbe, 0xf8, 0x85, 0xba, 0xe4, 0xb6, 0xea, 0x06,
             0x98, 0xf9, 0xc0, 0xd2, 0xac, 0x17, 0x19, 0x85,
             0x54, 0xdb, 0xe1, 0x3b, 0x3e, 0x85, 0x61, 0xee,
             0x31, 0xaf, 0x36, 0xa6, 0x04, 0xd3, 0x51, 0x21,
             0x09, 0x20]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        pmap = packet.parse()

        self.assertEqual(
            '13:00', packet.timestamp)

        self.assertTrue(
            'ethernet' in pmap)
        self.assertTrue(
            'ip' in pmap)
        self.assertTrue(
            'tcp' in pmap)

        self.assertEqual(
            pcap_packet.PCAPEthernet, type(pmap['ethernet']))
        self.assertEqual(
            pcap_packet.PCAPIP4, type(pmap['ip']))
        self.assertEqual(
            pcap_packet.PCAPTCP, type(pmap['tcp']))

        self.assertEqual(
            '08:00:27:c6:25:01', pmap['ethernet'].source_mac)
        self.assertEqual(
            '52:54:00:12:35:02', pmap['ethernet'].dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)
        self.assertEqual(
            '10.0.2.15', pmap['ip'].source_ip)
        self.assertEqual(
            '10.0.2.2', pmap['ip'].dest_ip)
        self.assertEqual(
            5, pmap['ip'].header_length)
        self.assertEqual(
            4, pmap['ip'].version)
        self.assertEqual(
            pcap_packet.IP4_PROTOCOL_TCP, pmap['ip'].protocol)
        self.assertEqual(
            pcap_packet.PCAPTCP, pmap['ip'].next_parse_recommendation)
        self.assertEqual(
            22, pmap['tcp'].source_port)
        self.assertEqual(
            53748, pmap['tcp'].dest_port)
        self.assertEqual(
            1377458300, pmap['tcp'].seq)
        self.assertEqual(
            1478831771, pmap['tcp'].ack)
        self.assertEqual(
            5, pmap['tcp'].data_offset)
        self.assertEqual(
            True,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ACK))
        self.assertEqual(
            True,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_PUSH))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_CWS))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ECE))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_FINAL))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_RESET))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_NS))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_SYN))
        self.assertEqual(
            False,
            pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_URGENT))
        self.assertEqual(
            40880,
            pmap['tcp'].window_size)
        self.assertEqual(
            None,
            pmap['tcp'].next_parse_recommendation)

    def test_full_packet_parsing_set_full_stack(self):
        full_eii_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0x45, 0x10, 0x00, 0x5c, 0x93, 0x06, 0x40, 0x00,
             0x40, 0x06, 0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f,
             0x0a, 0x00, 0x02, 0x02, 0x00, 0x16, 0xd1, 0xf4,
             0x52, 0x1a, 0x58, 0x7c, 0x58, 0x25, 0x2e, 0x9b,
             0x50, 0x18, 0x9f, 0xb0, 0x18, 0x5f, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x20, 0xb0, 0x2c, 0x08, 0xab,
             0x7f, 0x98, 0x3c, 0x58, 0x54, 0xeb, 0xde, 0x01,
             0xd1, 0xc7, 0xbe, 0xf8, 0x85, 0xba, 0xe4, 0xb6,
             0xea, 0x06, 0x98, 0xf9, 0xc0, 0xd2, 0xac, 0x17,
             0x19, 0x85, 0x54, 0xdb, 0xe1, 0x3b, 0x3e, 0x85,
             0x61, 0xee, 0x31, 0xaf, 0x36, 0xa6, 0x04, 0xd3,
             0x51, 0x21, 0x09, 0x20]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        pmap = packet.parse([pcap_packet.PCAPTCP,
                             pcap_packet.PCAPIP4,
                             pcap_packet.PCAPSLL])

        self.assertEqual(
            '13:00', packet.timestamp)
        self.assertTrue(
            'ethernet' in pmap)
        self.assertTrue(
            'ip' in pmap)
        self.assertTrue(
            'tcp' in pmap)

        self.assertEqual(
            pcap_packet.PCAPSLL, type(pmap['ethernet']))
        self.assertEqual(
            pcap_packet.PCAPIP4, type(pmap['ip']))
        self.assertEqual(
            pcap_packet.PCAPTCP, type(pmap['tcp']))

        self.assertEqual(
            '08:00:27:c6:25:01', pmap['ethernet'].source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', pmap['ethernet'].dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)
        self.assertEqual(
            '10.0.2.15', pmap['ip'].source_ip)
        self.assertEqual(
            '10.0.2.2', pmap['ip'].dest_ip)
        self.assertEqual(
            5, pmap['ip'].header_length)
        self.assertEqual(
            4, pmap['ip'].version)
        self.assertEqual(
            pcap_packet.IP4_PROTOCOL_TCP, pmap['ip'].protocol)
        self.assertEqual(
            pcap_packet.PCAPTCP, pmap['ip'].next_parse_recommendation)
        self.assertEqual(
            22, pmap['tcp'].source_port)
        self.assertEqual(
            53748, pmap['tcp'].dest_port)
        self.assertEqual(
            1377458300, pmap['tcp'].seq)
        self.assertEqual(
            1478831771, pmap['tcp'].ack)
        self.assertEqual(
            5, pmap['tcp'].data_offset)
        self.assertEqual(
            True, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ACK))
        self.assertEqual(
            True, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_PUSH))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_CWS))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ECE))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_FINAL))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_RESET))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_NS))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_SYN))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_URGENT))
        self.assertEqual(
            40880, pmap['tcp'].window_size)
        self.assertEqual(
            None, pmap['tcp'].next_parse_recommendation)

    def test_full_packet_parsing_set_partial_stack(self):
        full_eii_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0x45, 0x10, 0x00, 0x5c, 0x93, 0x06, 0x40, 0x00,
             0x40, 0x06, 0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f,
             0x0a, 0x00, 0x02, 0x02, 0x00, 0x16, 0xd1, 0xf4,
             0x52, 0x1a, 0x58, 0x7c, 0x58, 0x25, 0x2e, 0x9b,
             0x50, 0x18, 0x9f, 0xb0, 0x18, 0x5f, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x20, 0xb0, 0x2c, 0x08, 0xab,
             0x7f, 0x98, 0x3c, 0x58, 0x54, 0xeb, 0xde, 0x01,
             0xd1, 0xc7, 0xbe, 0xf8, 0x85, 0xba, 0xe4, 0xb6,
             0xea, 0x06, 0x98, 0xf9, 0xc0, 0xd2, 0xac, 0x17,
             0x19, 0x85, 0x54, 0xdb, 0xe1, 0x3b, 0x3e, 0x85,
             0x61, 0xee, 0x31, 0xaf, 0x36, 0xa6, 0x04, 0xd3,
             0x51, 0x21, 0x09, 0x20]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        pmap = packet.parse([pcap_packet.PCAPSLL])

        self.assertEqual(
            '13:00', packet.timestamp)
        self.assertTrue(
            'ethernet' in pmap)
        self.assertTrue(
            'ip' in pmap)
        self.assertTrue(
            'tcp' in pmap)

        self.assertEqual(
            pcap_packet.PCAPSLL, type(pmap['ethernet']))
        self.assertEqual(
            pcap_packet.PCAPIP4, type(pmap['ip']))
        self.assertEqual(
            pcap_packet.PCAPTCP, type(pmap['tcp']))

        self.assertEqual(
            '08:00:27:c6:25:01', pmap['ethernet'].source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', pmap['ethernet'].dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)
        self.assertEqual(
            '10.0.2.15', pmap['ip'].source_ip)
        self.assertEqual(
            '10.0.2.2', pmap['ip'].dest_ip)
        self.assertEqual(
            5, pmap['ip'].header_length)
        self.assertEqual(
            4, pmap['ip'].version)
        self.assertEqual(
            pcap_packet.IP4_PROTOCOL_TCP, pmap['ip'].protocol)
        self.assertEqual(
            pcap_packet.PCAPTCP, pmap['ip'].next_parse_recommendation)
        self.assertEqual(
            22, pmap['tcp'].source_port)
        self.assertEqual(
            53748, pmap['tcp'].dest_port)
        self.assertEqual(
            1377458300, pmap['tcp'].seq)
        self.assertEqual(
            1478831771, pmap['tcp'].ack)
        self.assertEqual(
            5, pmap['tcp'].data_offset)
        self.assertEqual(
            True, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ACK))
        self.assertEqual(
            True, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_PUSH))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_CWS))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_ECE))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_FINAL))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_RESET))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_NS))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(pcap_packet.TCP_PROTOCOL_FLAG_SYN))
        self.assertEqual(
            False, pmap['tcp'].is_flag_set(
                pcap_packet.TCP_PROTOCOL_FLAG_URGENT))
        self.assertEqual(
            40880, pmap['tcp'].window_size)
        self.assertEqual(
            None, pmap['tcp'].next_parse_recommendation)

    def test_full_packet_parsing_l2_bad_length(self):
        full_eii_packet_data = \
            [0x52, 0x54, 0x00, 0x12, 0x35, 0x02, 0x08, 0x00,
             0x27, 0xc6]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        self.assertRaises(
            pcap_packet.PacketParsingException, packet.parse)

        emap = packet.extra_data

        self.assertEqual(
            1, len(emap['parse_errors.ethernet']))
        self.assertRegexpMatches(
            emap['parse_errors.ethernet'][0], 'must at least be')

        self.assertEqual(
            '13:00', packet.timestamp)

    def test_full_packet_parsing_l3_bad_length(self):
        full_eii_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0x45, 0x10, 0x00, 0x5c, 0x93, 0x06]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        self.assertRaises(
            pcap_packet.PacketParsingException,
            packet.parse,
            [pcap_packet.PCAPSLL])

        pmap = packet.layer_data
        """ :type: dict[str, PCAPPacket.PCAPEncapsulatedLayer] """
        emap = packet.extra_data

        self.assertEqual(
            1, len(emap['parse_errors.ip']))
        self.assertRegexpMatches(
            emap['parse_errors.ip'][0], 'must at least be')

        self.assertEqual(
            '13:00', packet.timestamp)
        self.assertTrue(
            'ethernet' in pmap)

        self.assertEqual(pcap_packet.PCAPSLL, type(pmap['ethernet']))

        ether_pmap = pmap['ethernet']
        """ :type: PCAPPacket.PCAPEthernet """
        self.assertEqual(
            '08:00:27:c6:25:01', ether_pmap.source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', ether_pmap.dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)

    def test_full_packet_parsing_l3_parse_error(self):
        full_eii_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0x4f, 0x10, 0x00, 0x5c, 0x93, 0x06, 0x40, 0x00,
             0x40, 0x06, 0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f,
             0x0a, 0x00, 0x02, 0x02, 0x00, 0x16, 0xd1, 0xf4,
             0x52, 0x1a, 0x58, 0x7c, 0x58, 0x25, 0x2e, 0x9b,
             0x50, 0x18, 0x9f, 0xb0, 0x18, 0x5f, 0x00, 0x00,
             0x00, 0x00, 0x00]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        self.assertRaises(
            pcap_packet.PacketParsingException,
            packet.parse,
            [pcap_packet.PCAPSLL])

        pmap = packet.layer_data
        emap = packet.extra_data

        self.assertEqual(
            1, len(emap['parse_errors.ip']))
        self.assertRegexpMatches(
            emap['parse_errors.ip'][0], 'longer than the packet size')

        self.assertEqual(
            '13:00', packet.timestamp)
        self.assertTrue(
            'ethernet' in pmap)

        self.assertEqual(
            pcap_packet.PCAPSLL, type(pmap['ethernet']))
        ether_pmap = pmap['ethernet']
        """ :type: pcap_packet.PCAPEthernet """
        self.assertEqual(
            '08:00:27:c6:25:01', ether_pmap.source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', ether_pmap.dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)

    def test_full_packet_parsing_l3_parse_error2(self):
        full_eii_packet_data = \
            [0x00, 0x04, 0x00, 0x01, 0x00, 0x06, 0x08, 0x00,
             0x27, 0xc6, 0x25, 0x01, 0x00, 0x00, 0x08, 0x00,
             0x41, 0x10, 0x00, 0x5c, 0x93, 0x06, 0x40, 0x00,
             0x40, 0x06, 0x8f, 0x75, 0x0a, 0x00, 0x02, 0x0f,
             0x0a, 0x00, 0x02, 0x02, 0x00, 0x16, 0xd1, 0xf4,
             0x52, 0x1a, 0x58, 0x7c, 0x58, 0x25, 0x2e, 0x9b,
             0x50, 0x18, 0x9f, 0xb0, 0x18, 0x5f, 0x00, 0x00,
             0x00, 0x00, 0x00]

        packet = pcap_packet.PCAPPacket(full_eii_packet_data, '13:00')
        self.assertRaises(
            pcap_packet.PacketParsingException,
            packet.parse,
            [pcap_packet.PCAPSLL])

        pmap = packet.layer_data
        emap = packet.extra_data

        self.assertEqual(
            1, len(emap['parse_errors.ip']))
        self.assertRegexpMatches(
            emap['parse_errors.ip'][0], 'field must be at least')

        self.assertEqual(
            '13:00', packet.timestamp)
        self.assertTrue(
            'ethernet' in pmap)

        self.assertEqual(
            pcap_packet.PCAPSLL, type(pmap['ethernet']))

        ether_pmap = pmap['ethernet']
        """ :type: pcap_packet.PCAPEthernet """
        self.assertEqual(
            '08:00:27:c6:25:01', ether_pmap.source_mac)
        self.assertEqual(
            '00:00:00:00:00:00', ether_pmap.dest_mac)
        self.assertEqual(
            pcap_packet.PCAPIP4, pmap['ethernet'].next_parse_recommendation)


run_unit_test(PCAPPacketTest)
