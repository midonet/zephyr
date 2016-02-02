# Copyright 2015 Midokura SARL
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

from common.Exceptions import *

ETHERNET_PROTOCOL_TYPE_IP4 = 0x0800
ETHERNET_PROTOCOL_TYPE_ARP = 0x0806
ETHERNET_PROTOCOL_TYPE_RARP = 0x8035
ETHERNET_PROTOCOL_TYPE_IP6 = 0x86DD

ARP_PROTOCOL_HW_TYPE_EHTERNET = 1

IP4_PROTOCOL_ICMP = 1
IP4_PROTOCOL_TCP = 6
IP4_PROTOCOL_UDP = 17

TCP_PROTOCOL_FLAG_NS = 0x100
TCP_PROTOCOL_FLAG_CWS = 0x80
TCP_PROTOCOL_FLAG_ECE = 0x40
TCP_PROTOCOL_FLAG_URGENT = 0x20
TCP_PROTOCOL_FLAG_ACK = 0x10
TCP_PROTOCOL_FLAG_PUSH = 0x8
TCP_PROTOCOL_FLAG_RESET = 0x4
TCP_PROTOCOL_FLAG_SYN = 0x2
TCP_PROTOCOL_FLAG_FINAL = 0x1

ARP_PROTOCOL_OPERATION_REQUEST = 1
ARP_PROTOCOL_OPERATION_REPLY = 2

ICMP_PROTOCOL_TYPE_ECHO_REPLY= 0
ICMP_PROTOCOL_TYPE_ECHO_REQUEST = 8
ICMP_PROTOCOL_TYPE_DESTINATION_UNREACHABLE = 3

ICMP_PROTOCOL_DU_CODE_NETWORK_UNREACHABLE = 0
ICMP_PROTOCOL_DU_CODE_HOST_UNREACHABLE = 1
ICMP_PROTOCOL_DU_CODE_PROTOCOL_UNREACHABLE = 2
ICMP_PROTOCOL_DU_CODE_PORT_UNREACHABLE = 3
ICMP_PROTOCOL_DU_CODE_FRAGMENTATION_REQD = 4
ICMP_PROTOCOL_DU_CODE_SOURCE_ROUTE_FAILED = 5
ICMP_PROTOCOL_DU_CODE_DEST_NETWORK_UNKNOWN = 6
ICMP_PROTOCOL_DU_CODE_DEST_HOST_UNKNOWN = 7
ICMP_PROTOCOL_DU_CODE_SOURCE_HOST_ISOLATED = 8
ICMP_PROTOCOL_DU_CODE_NETWORK_ADMIN_PROHIBIT = 9
ICMP_PROTOCOL_DU_CODE_HOST_ADMIN_PROHIBIT = 10
ICMP_PROTOCOL_DU_CODE_NETWORK_UNREACHABLE_TOS = 11
ICMP_PROTOCOL_DU_CODE_HOST_UNREACHABLE_TOS = 12
ICMP_PROTOCOL_DU_CODE_COMM_PROHIBIT = 13
ICMP_PROTOCOL_DU_CODE_HOST_PRECEDENCE_VIOLATION = 14
ICMP_PROTOCOL_DU_CODE_PRECEDENCE_CUTOFF = 15


class PCAPPacket(object):

    @staticmethod
    def char8_to_int16(char_msb, char_lsb):
        """
        Converts two 'char's into a single int in "Big-Endian" fashion and returns the new 16-bit integer.
        :param char_msb: int Most significant byte
        :param char_lsb: int Least significant byte
        :return: int
        """
        return (char_msb * 0x100) + char_lsb

    @staticmethod
    def char8_to_int32(char_msbh, char_msbl, char_lsbh, char_lsbl):
        """
        Converts four 'char's into a single int in "Big-Endian" fashion and returns the new 32-bit integer.
        :param char_msbh: int Most significant byte
        :param char_msbl: int 2nd most significant byte
        :param char_lsbh: int 3rd byte
        :param char_lsbl: int Least significant byte
        :return: int
        """
        ret = (char_msbh * 0x1000000)
        ret += (char_msbl * 0x10000)
        ret += (char_lsbh * 0x100)
        ret += char_lsbl
        return ret

    @staticmethod
    def char8_to_ip4(char1, char2, char3, char4):
        """
        Converts four 'char's (passed in as Python ints) into a dotted IP string.
        :param char1: int The first byte in the IP ('A' in A.B.C.D)
        :param char2: int The second byte in the IP ('B' in A.B.C.D)
        :param char1: int The third byte in the IP ('C' in A.B.C.D)
        :param char2: int The fourth byte in the IP ('D' in A.B.C.D)
        :return: str
        """
        return str(char1) + '.' + str(char2) + '.' + str(char3) + '.' + str(char4)

    @staticmethod
    def char8_to_mac_address(char1, char2, char3, char4, char5, char6):
        """
        Converts six 'char's (pass as Python ints) into a MAC Address string (using hexadecimal notation)
        :param char1: int First byte in the MAC ('AA' in AA:BB:CC:DD:EE:FF)
        :param char2: int Second byte in the MAC ('BB' in AA:BB:CC:DD:EE:FF)
        :param char3: int Third byte in the MAC ('CC' in AA:BB:CC:DD:EE:FF)
        :param char4: int Fourth byte in the MAC ('DD' in AA:BB:CC:DD:EE:FF)
        :param char5: int Fifth byte in the MAC ('EE' in AA:BB:CC:DD:EE:FF)
        :param char6: int Sixth byte in the MAC ('FF' in AA:BB:CC:DD:EE:FF)
        :return: str
        """
        return '{0:02x}:{1:02x}:{2:02x}:{3:02x}:{4:02x}:{5:02x}'.format(char1, char2, char3,
                                                                        char4, char5, char6)

    def __init__(self, packet_data, timestamp):
        """
        :param packet_data: list[int]
        :param timestamp: str
        """
        self.timestamp = timestamp
        self.packet_data = packet_data
        self.layer_data = {}
        """ :type: dict[str, PCAPEncapsulatedLayer] """
        self.extra_data = {}
        """ :type: dict[str, list[str]] """

    def __iter__(self):
        return iter(self.layer_data)

    def to_str(self):
        ret_str = 'PACKET { time[' + str(self.timestamp) + '] '
        for n, l in self.layer_data.iteritems():
            ret_str += '<layer [' + n + '] ' + l.to_str() + '>'
        ret_str += '}'
        return ret_str

    def get_data(self):
        return self.layer_data

    def parse(self, parse_class_stack=None):
        """
        :param parse_class_stack: list[class] Stack of classes to parse packet (highest layer first in list)
        :return: dict[str, PCAPEncapsulatedLayer]
        """

        self.extra_data['parse_classes'] = []
        self.extra_data['parse_types'] = []

        # Start parsing with the whole packet (starting from Link-Layer)
        current_data = self.packet_data

        # By default, the parsing stack is None, which tells us to figure it out automatically,
        #  so let's start with Ethernet_II, as it's the most common link player protocol. If it
        #  is empty at any point, that means to just use the recommended parser, which in this case
        #  would mean to use Ethernet, since it's the first step.
        if parse_class_stack is None or len(parse_class_stack) == 0:
            parse_class_name = PCAPEthernet
        else:
            # Otherwise, let's pop the first parsing class and continue
            parse_class_name = parse_class_stack.pop()

        # If there are no more parsers to run in the stack, finish up
        while parse_class_name is not None:

            #Check type and set up some extra information about the classes used to parse
            if not isinstance(parse_class_name(), PCAPEncapsulatedLayer):
                raise ArgMismatchException('Parsing classes must be of type "PCAPEncapsulatedLayer"')

            self.extra_data['parse_classes'].append(parse_class_name.__name__)
            self.extra_data['parse_types'].append(parse_class_name.layer_name())
            self.extra_data['parse_errors.' + parse_class_name.layer_name()] = []

            # Instantiate the object based on the class given as the "next parser"
            link_obj = parse_class_name()
            """ :type: PCAPEncapsulatedLayer"""

            try:
                # Parse the current packet data and set the result as the new packet data for the
                #  next layer to parse.
                current_data = link_obj.parse_layer(current_data)
            except PacketParsingException as e:
                self.extra_data['parse_errors.' + parse_class_name.layer_name()].append(e.info)
                if e.fatal is True:
                    raise e

            # Set the item in the data map with the parsed object keyed to the name
            #  the object itself uses to access the data
            self.layer_data[parse_class_name.layer_name()] = link_obj

            # If the last parser recommended a parser for the rest of the data and there
            #  were no other parsers configured manually to run, then add the recommended
            #  parser for the next step, otherwise, just use whatever we were told to use.

            # Get the next parser's class name.  If stack is empty (or not defined), use the
            #  next recommended parser. If the next recommended parser is "None", that means
            #  we are finished parsing and exit the loop.
            if parse_class_stack is None or len(parse_class_stack) == 0:
                parse_class_name = link_obj.next_parse_recommendation
            else:
                # If the stack has a next step, use that instead.  If it's "None", that signals us
                #  to stop parsing and finish the loop.
                parse_class_name = parse_class_stack.pop()

        return self.layer_data

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return self.to_str()

class PCAPEncapsulatedLayer(object):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        raise PacketParsingException("Base layer class shouldn't be used directly.  "
                                     "Use a specific layer type instead.",
                                     fatal=False)

    def __init__(self):
        self.next_parse_recommendation = None

    def to_str(self):
        return ''

    def parse_layer(self, packet_data):
        """
        :param packet_data: list[int] Array of int representing the bytes in the packet
        :return: list[int]
        """
        raise PacketParsingException("Base layer class shouldn't be used directly.  "
                                     "Use a specific layer type instead.",
                                     fatal=False)


class PCAPEthernet(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'ethernet'

    def __init__(self):
        super(PCAPEthernet, self).__init__()
        self.dest_mac = ''
        """ :type: str """
        self.source_mac = ''
        """ :type: str """
        self.type = 0
        """ :type: int """

    def to_str(self):
        return 's_mac[' + self.source_mac + '] ' + 'd_mac[' + self.dest_mac + '] ' + \
               'type[0x' + '{0:04x}'.format(self.type) + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        Ethernet_II frame structure:
        6 bytes - dest_mac
        6 bytes - source mac
        2 bytes - type (should be 0x0800 for IP and 0x0806 for ARP)
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 14:
            raise PacketParsingException('Ethernet layer data must at least be 14 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.dest_mac = PCAPPacket.char8_to_mac_address(*packet_data[0:6])
        self.source_mac = PCAPPacket.char8_to_mac_address(*packet_data[6:12])
        self.type = PCAPPacket.char8_to_int16(*packet_data[12:14])

        # Otherwise, judge based on the type from our built-ins
        if self.type == 0x0800:
            self.next_parse_recommendation = PCAPIP4
        elif self.type == 0x0806:
            self.next_parse_recommendation = PCAPARP
        else:
            raise PacketParsingException("No known handler for Ethernet type: " + str(self.type), fatal=False)

        return packet_data[14:]


class PCAPSLL(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'ethernet'

    def __init__(self):
        super(PCAPSLL, self).__init__()
        self.dest_mac = ''
        """ :type: str """
        self.source_mac = ''
        """ :type: str """
        self.type = 0
        """ :type: int """

    def to_str(self):
        return 's_mac[' + self.source_mac + '] ' + 'd_mac[' + self.dest_mac + '] ' + \
               'type[0x' + '{0:04x}'.format(self.type) + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If Linux-Cooked (SLL) link-layer (i.e. the 'any' interface was used):
        6 bytes - Linux Cooked Protocol info
        6 bytes - source mac
        2 bytes - padding (00 00)
        2 bytes - type (should be 0x0800 for IP and 0x0806 for ARP)
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 16:
            raise PacketParsingException("'Linux-cooked' layer data must at least be 16 bytes, but packet size is [" +
                                         str(len(packet_data)) + ']', fatal=True)

        self.dest_mac = PCAPPacket.char8_to_mac_address(*([0] * 6))
        self.source_mac = PCAPPacket.char8_to_mac_address(*packet_data[6:12])
        self.type = PCAPPacket.char8_to_int16(packet_data[14], packet_data[15])

        # Otherwise, judge based on the type from our built-ins
        if self.type == 0x0800:
            self.next_parse_recommendation = PCAPIP4
        elif self.type == 0x0806:
            self.next_parse_recommendation = PCAPARP
        else:
            raise PacketParsingException("Encapsulated type [" + str(self.type) + "] unknown", fatal=False)

        return packet_data[16:]


class PCAPIP4(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'ip'

    def __init__(self):
        super(PCAPIP4, self).__init__()
        self.version = 4
        """ :type: int """
        self.header_length = 0
        """ :type: int """
        self.protocol = 0
        """ :type: int """
        self.source_ip = ''
        """ :type: str """
        self.dest_ip = ''
        """ :type: str """

    def to_str(self):
        return 'ver[' + str(self.version) + '] ' + 'h_len[' + str(self.header_length) + '] ' + \
               'proto[' + str(self.protocol) + '] ' + 's_ip[' + self.source_ip + '] ' + \
               'd_ip[' + self.dest_ip + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If IP, the packet will look like this with word, word offset, and total offset followed by size of field):
        word 1, 0: total 0:  1 byte -  Version + header length (length is in 4-byte words)
        word 1, 1: total 1:  1 byte -  DSCP + ECN
        word 1, 2: total 2:  2 bytes - Total Length
        word 2, 0: total 4:  2 bytes - ID
        word 2, 2: total 6:  2 bytes - Flags and Fragment Offset
        word 3, 0: total 8:  1 byte -  TTL
        word 3, 1: total 9:  1 byte -  Protocol
        word 3, 2: total 10: 2 bytes - Header Checksum
        word 4, 0: total 12: 4 bytes - Source IP
        word 5, 0: total 16: 4 bytes - Destination IP
        word 6-20: total 20-160: 0-40 bytes - Options
        20 - 60: Data
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 20:
            raise PacketParsingException('IP layer data must at least be 20 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.version = (packet_data[0] & 0xf0) >> 4

        # Version must be either 4 or 6, no exceptions
        if self.version != 4 and self.version != 6:
            raise PacketParsingException('IP version must be either 4 or 6, but it was [' +
                                         str(self.version) + ']', fatal=True)

        self.header_length = packet_data[0] & 0x0f

        # Do a sanity check on header length vs. packet size
        if self.header_length < 5:
            raise PacketParsingException('IP header length field must be at least 5, but it was [' +
                                         str(self.header_length), fatal=True)

        if (self.header_length * 4) > len(packet_data):
            raise PacketParsingException('IP header length field specifies length [' +
                                         str(self.header_length) + '] longer than the packet size [' +
                                         str(len(packet_data)) + ']!', fatal=True)

        self.protocol = packet_data[9]

        # Otherwise, judge based on the type from our built-ins
        if self.protocol == IP4_PROTOCOL_TCP:
            self.next_parse_recommendation = PCAPTCP
        elif self.protocol == IP4_PROTOCOL_UDP:
            self.next_parse_recommendation = PCAPUDP
        elif self.protocol == IP4_PROTOCOL_ICMP:
            self.next_parse_recommendation = PCAPICMP
        else:
            raise PacketParsingException("IP protocol [" + str(self.protocol) + "] unknown", fatal=False)

        self.source_ip = PCAPPacket.char8_to_ip4(packet_data[12], packet_data[13], packet_data[14], packet_data[15])
        self.dest_ip = PCAPPacket.char8_to_ip4(packet_data[16], packet_data[17], packet_data[18], packet_data[19])

        # Remember, header length is in 4-octet words, so multiply by 4 to get the data's starting byte
        return packet_data[(self.header_length * 4):]


class PCAPARP(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'arp'

    def __init__(self):
        super(PCAPARP, self).__init__()
        self.hw_type = 0
        """ :type: int """
        self.proto_type = 0
        """ :type: int """
        self.hw_addr_length = 0
        """ :type: int """
        self.proto_addr_length = 0
        """ :type: int """
        self.operation = 0
        """ :type: int """
        self.sender_hw_addr_raw = ''
        """ :type: list[int] """
        self.sender_hw_addr_ether = ''
        """ :type: str """
        self.sender_proto_addr_raw = ''
        """ :type: list[int] """
        self.sender_ip_addr = ''
        """ :type: str """
        self.target_hw_addr_raw = ''
        """ :type: list[int] """
        self.target_hw_addr_ether = ''
        """ :type: str """
        self.target_proto_addr_raw = ''
        """ :type: list[int] """
        self.target_ip_addr = ''
        """ :type: str """

    def to_str(self):
        return 'hw_type[' + str(self.hw_type) + '] ' + 'p_type[' + str(self.proto_type) + '] ' + \
               'op[' + str(self.operation) + '] ' + 's_mac[' + self.sender_hw_addr_ether + '] ' + \
               'd_mac[' + self.sender_hw_addr_ether + '] ' + 's_ip[' + self.sender_ip_addr + '] ' + \
               'd_ip[' + self.target_ip_addr + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If IP, the packet will look like this with word, word offset, and total offset followed by size of field):
        word 1, 0: total 0:  2 bytes - Hardware Type
        word 1, 2: total 2:  2 bytes - Protocol Type
        word 2, 0: total 4:  1 byte  - Hardware addr length
        word 2, 1: total 5:  1 byte  - Protocol addr length
        word 2, 2: total 6:  2 bytes -  Operation
        word 3, 0: total 8:  HW-ADDR-LENGTH bytes - Sender HW address
        word 4, 2: total (14):  PROTO-ADDR-LENGTH bytes - Sender Protocol address
        word 5, 2: total (18):  HW-ADDR-LENGTH bytes - Target HW address
        word 7, 0: total (24):  PROTO-ADDR-LENGTH bytes - Target Protocol address
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 12:
            raise PacketParsingException('ARP layer data must at least be 12 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.hw_type = PCAPPacket.char8_to_int16(packet_data[0], packet_data[1])
        self.proto_type = PCAPPacket.char8_to_int16(packet_data[2], packet_data[3])
        self.hw_addr_length = packet_data[4]
        self.proto_addr_length = packet_data[5]
        self.operation = PCAPPacket.char8_to_int16(packet_data[6], packet_data[7])

        # Sanity check on packet length now that we know the sizes of the HW and Protocol addresses
        expected_size = (8 + (2 * self.hw_addr_length) + (2 * self.proto_addr_length))
        if len(packet_data) < expected_size:
            raise PacketParsingException('ARP packet size is expected to be [' + str(expected_size) +
                                         '] based on set HW and Proto address lengths, but the real packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        sender_hw_addr_base = 8
        sender_proto_addr_base = sender_hw_addr_base + self.hw_addr_length
        target_hw_addr_base = sender_proto_addr_base + self.proto_addr_length
        target_proto_addr_base = target_hw_addr_base + self.hw_addr_length
        target_proto_addr_finish = target_proto_addr_base + self.proto_addr_length

        self.sender_hw_addr_raw = packet_data[sender_hw_addr_base:sender_proto_addr_base]
        self.sender_proto_addr_raw = packet_data[sender_proto_addr_base:target_hw_addr_base]
        self.target_hw_addr_raw = packet_data[target_hw_addr_base:target_proto_addr_base]
        self.target_proto_addr_raw = packet_data[target_proto_addr_base:target_proto_addr_finish]

        if self.hw_type == ARP_PROTOCOL_HW_TYPE_EHTERNET:
            self.sender_hw_addr_ether = PCAPPacket.char8_to_mac_address(*self.sender_hw_addr_raw)
            self.target_hw_addr_ether = PCAPPacket.char8_to_mac_address(*self.target_hw_addr_raw)

        if self.proto_type == ETHERNET_PROTOCOL_TYPE_IP4:
            self.sender_ip_addr = PCAPPacket.char8_to_ip4(*self.sender_proto_addr_raw)
            self.target_ip_addr = PCAPPacket.char8_to_ip4(*self.target_proto_addr_raw)

        self.next_parse_recommendation = None

        if len(packet_data) > target_proto_addr_finish:
            raise PacketParsingException('ARP packet has junk data at end of packet [' +
                                         ', '.join(['0x{0:02x}'.format(i)
                                                    for i in packet_data[target_proto_addr_finish:]]),
                                         fatal=False)

        # Should be empty, but just in case...
        return []


class PCAPTCP(PCAPEncapsulatedLayer):

    def is_flag_set(self, flag):
        return self.flags & flag != 0

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'tcp'

    def __init__(self):
        super(PCAPTCP, self).__init__()
        self.source_port = 0
        """ :type: int """
        self.dest_port = 0
        """ :type: int """
        self.seq = 0
        """ :type: int """
        self.ack = 0
        """ :type: int """
        self.data_offset = 0
        """ :type: int """
        self.flags = 0
        """ :type: int """
        self.window_size = 0
        """ :type: int """

    def to_str(self):
        return 's_port[' + str(self.source_port) + '] ' + 'd_port[' + str(self.dest_port) + '] ' + \
               'seq[' + str(self.seq) + '] ' + 'ack[' + str(self.ack) + '] ' + \
               'd_off[' + str(self.data_offset) + '] ' + 'flags[0x' + '{0:02x}'.format(self.flags) + '] ' + \
               'w_size[' + str(self.window_size) + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If TCP, the packet will look like this:
        word 1, 0: total 0:  2 bytes - Source port
        word 1, 2: total 2:  2 bytes - Destination port
        word 2, 0: total 4:  4 bytes - Sequence Number
        word 3, 0: total 8:  4 bytes - Acknoweldge Number
        word 4, 0: total 12: 1 byte  - Data Offset + 000 + NS Flag
        word 4, 1: total 13: 1 byte -  CWS, ECE, URG, ACK, PSH, RST, SYN, FIN Flags
        word 4, 2: total 14: 2 bytes - Window Size
        word 5, 0: total 16: 2 bytes - Checksum
        word 5, 2: total 18: 2 bytes - Urgent Pointer
        word 6-20: total 20-160: 0-40 bytes - Options
        20 - 60: Data
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 20:
            raise PacketParsingException('TCP layer data must at least be 20 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.source_port = PCAPPacket.char8_to_int16(packet_data[0], packet_data[1])
        self.dest_port = PCAPPacket.char8_to_int16(packet_data[2], packet_data[3])
        self.seq = PCAPPacket.char8_to_int32(packet_data[4], packet_data[5], packet_data[6], packet_data[7])
        self.ack = PCAPPacket.char8_to_int32(packet_data[8], packet_data[9], packet_data[10], packet_data[11])
        self.data_offset = (packet_data[12] & 0xF0) >> 4

        #Sanity check on data offset
        if self.data_offset < 5:
            raise PacketParsingException('TCP data offset field must be at least 5, but it was [' +
                                         str(self.data_offset), fatal=True)

        if self.data_offset > len(packet_data):
            raise PacketParsingException('TCP data offset field specifies length [' +
                                         str(self.data_offset) + '] longer than the packet size [' +
                                         str(len(packet_data)) + ']!', fatal=True)

        self.flags = ((packet_data[12] & 0x1) * 0xFF) + packet_data[13]
        self.window_size = PCAPPacket.char8_to_int16(packet_data[14], packet_data[15])

        # TCP is the last parsed packet in our stack.  Can add Layer 5-7 here (HTTP, SOAP, etc.)
        self.next_parse_recommendation = None

        # Remember, header length is in 4-octet words, so multiply by 4 to get the data's starting byte
        return packet_data[(self.data_offset * 4):]


class PCAPUDP(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'udp'

    def __init__(self):
        super(PCAPUDP, self).__init__()
        self.source_port = 0
        """ :type: int """
        self.dest_port = 0
        """ :type: int """
        self.length = 0
        """ :type: int """

    def to_str(self):
        return 's_port[' + str(self.source_port) + '] ' + 'd_port[' + str(self.dest_port) + '] ' + \
               'len[' + str(self.length) + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If UDP, the packet will look like this:
        word 1, 0: total 0:  2 bytes - Source port
        word 1, 2: total 2:  2 bytes - Destination port
        word 2, 0: total 4:  2 bytes - Length
        word 2, 2: total 6:  2 bytes - Checksum
        8 -> : Data
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 8:
            raise PacketParsingException('UDP layer data must at least be 8 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.source_port = PCAPPacket.char8_to_int16(packet_data[0], packet_data[1])
        self.dest_port = PCAPPacket.char8_to_int16(packet_data[2], packet_data[3])
        self.length = PCAPPacket.char8_to_int16(packet_data[4], packet_data[5])

        # UDP is the last parsing step in the standard TCP/IP stack
        self.next_parse_recommendation = None

        # Remember, header length is in 4-octet words, so multiply by 4 to get the data's starting byte
        return packet_data[8:]


class PCAPICMP(PCAPEncapsulatedLayer):

    @staticmethod
    def layer_name():
        """
        :return: str
        """
        return 'icmp'

    def __init__(self):
        super(PCAPICMP, self).__init__()
        self.type = 0
        """ :type: int """
        self.code = 0
        """ :type: int """
        self.header_data = []
        """ :type: list[int] """

    def to_str(self):
        return 'type[' + str(self.type) + '] ' + 'code[' + str(self.code) + '] ' + \
               'h_data[' + str(self.header_data) + ']'

    def parse_layer(self, packet_data):
        """
        :type packet_data: list[int]
        :return: list[int]

        If UDP, the packet will look like this:
        word 1, 0: total 0: 1 byte  - Type
        word 1, 1: total 1: 1 byte  - Code
        word 1, 2: total 2: 2 bytes - Checksum
        word 2, 0: total 4: 4 bytes - Rest of header
        8 -> : Data
        """
        # First, check length of packet to make sure it is at least long enough for the header
        if len(packet_data) < 8:
            raise PacketParsingException('ICMP layer data must at least be 8 bytes, but packet size is [' +
                                         str(len(packet_data)) + ']', fatal=True)

        self.type = packet_data[0]
        self.code = packet_data[1]
        self.header_data = packet_data[4:8]

        # ICMP is the last parsing step in the standard TCP/IP stack
        self.next_parse_recommendation = None

        # Remember, header length is in 4-octet words, so multiply by 4 to get the data's starting byte
        return packet_data[8:]
