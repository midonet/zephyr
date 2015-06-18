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


class PCAP_Rule(object):
    def __init__(self):
        pass

    def to_str(self):
        raise ArgMismatchException('All Rules should override the "to_str" method!')


class PCAP_Simple(PCAP_Rule):
    def __init__(self, val):
        """
        :param val: str
        """
        super(PCAP_Simple, self).__init__()
        self.explicit_val = val

    def to_str(self):
        return self.explicit_val


class PCAP_Null(PCAP_Simple):
    def __init__(self):
        super(PCAP_Null, self).__init__(val='')


class PCAP_BinaryBoolean(PCAP_Rule):
    def __init__(self, operation, rule_set):
        """
        :param operation: str
        :param rule_set: list[PS_Rule]
        """
        super(PCAP_BinaryBoolean, self).__init__()
        self.operation = operation
        self.rule_set = rule_set

    def to_str(self):
        if len(self.rule_set) < 2:
            return ''.join([r'\( ' + i.to_str() + r' \)' for i in self.rule_set])
        return (' ' + self.operation + ' ').join([r'\( ' + i.to_str() + r' \)' for i in self.rule_set])


class PCAP_And(PCAP_BinaryBoolean):
    def __init__(self, rule_set):
        """
        :param rule_set: list[PS_Rule]
        """
        super(PCAP_And, self).__init__('and', rule_set)


class PCAP_Or(PCAP_BinaryBoolean):
    def __init__(self, rule_set):
        """
        :param rule_set: list[PS_Rule]
        """
        super(PCAP_Or, self).__init__('or', rule_set)


class PCAP_Not(PCAP_Rule):
    def __init__(self, rule):
        """
        :param rule: PS_Rule
        """
        super(PCAP_Not, self).__init__()
        self.rule = rule

    def to_str(self):
        return 'not \( ' + self.rule.to_str() + r' \)'


class PCAP_Comparison(PCAP_Rule):
    def __init__(self, operation, lhs, rhs):
        """
        :param operation: str
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_Comparison, self).__init__()
        self.operation = operation
        self.lhs = lhs
        self.rhs = rhs

    def to_str(self):
        return str(self.lhs) + ' ' + str(self.operation) + ' ' + str(self.rhs)


class PCAP_GreaterThanEqual(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_GreaterThanEqual, self).__init__('\>=', lhs, rhs)


class PCAP_GreaterThan(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_GreaterThan, self).__init__('\>', lhs, rhs)


class PCAP_Equal(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_Equal, self).__init__('=', lhs, rhs)


class PCAP_NotEqual(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_NotEqual, self).__init__('!=', lhs, rhs)


class PCAP_LessThan(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_LessThan, self).__init__('\<', lhs, rhs)


class PCAP_LessThanEqual(PCAP_Comparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(PCAP_LessThanEqual, self).__init__('\<=', lhs, rhs)


class PCAP_PrimitiveTypeRule(PCAP_Rule):
    def __init__(self, param, proto='', source=False, dest=False):
        """
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PCAP_PrimitiveTypeRule, self).__init__()
        self.proto = proto
        self.source = source
        self.dest = dest
        self.param = param

    def to_str(self):
        cmd = self.proto + ' ' if self.proto != '' else ''
        if not self.source and not self.dest:
            cmd += ''
        elif self.source and not self.dest:
            cmd += 'src '
        elif not self.source and self.dest:
            cmd += 'dst '
        elif self.source and self.dest:
            cmd += 'src and dst '
        return cmd + self.param


class PCAP_Host(PCAP_PrimitiveTypeRule):
    def __init__(self, host, proto='', source=False, dest=False):
        """
        :param host: str
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PCAP_Host, self).__init__('host ' + host, proto, source, dest)


class PCAP_PortRange(PCAP_PrimitiveTypeRule):
    def __init__(self, start_port, end_port, proto='', source=False, dest=False):
        """
        :param start_port: int
        :param end_port: int
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PCAP_PortRange, self).__init__('portrange ' + str(start_port) + '-' + str(end_port),
                                           proto, source, dest)


class PCAP_Port(PCAP_PrimitiveTypeRule):
    def __init__(self, port, proto='', source=False, dest=False):
        """
        :param port: int
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PCAP_Port, self).__init__('port ' + str(port), proto, source, dest)


class PCAP_Net(PCAP_PrimitiveTypeRule):
    def __init__(self, net, mask='', proto='', source=False, dest=False):
        """
        :param net: str
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PCAP_Net, self).__init__('net ' + net + (' mask ' + mask if mask != '' else ''),
                                     proto, source, dest)


class PCAP_PrimitiveProtoRule(PCAP_Rule):
    def __init__(self, base_proto, filter_proto):
        """
        :param base_proto: str Either 'ip' or 'ether'
        :param filter_proto: str For 'ip', can be 'tcp, icmp, udp'.  For 'ether' can be 'ip', 'arp', 'stp'
        """
        super(PCAP_PrimitiveProtoRule, self).__init__()
        self.base_proto = base_proto
        self.filter_proto = filter_proto

    def to_str(self):
        return self.base_proto + ' proto ' + self.filter_proto


class PCAP_SimpleProto(PCAP_PrimitiveProtoRule):
    def __init__(self, proto):
        """
        :param proto: str One of 'tcp', 'icmp', or 'udp'
        """
        super(PCAP_SimpleProto, self).__init__('', '\\\\' + proto)


class PCAP_IPProto(PCAP_PrimitiveProtoRule):
    def __init__(self, proto):
        """
        :param proto: str One of 'tcp', 'icmp', or 'udp'
        """
        super(PCAP_IPProto, self).__init__('ip', proto)


class PCAP_EtherProto(PCAP_PrimitiveProtoRule):
    def __init__(self, proto):
        """
        :param proto: str One of 'ip', 'arp', or 'stp'
        """
        super(PCAP_EtherProto, self).__init__('ether', proto)


class PCAP_PrimitiveCast(PCAP_Rule):
    def __init__(self, type, proto='ether'):
        """
        :param type: str Either 'broadcast' or 'multicast'
        :param proto: str Either 'ip' or 'ether'
        """
        super(PCAP_PrimitiveCast, self).__init__()
        self.type = type
        self.proto = proto

    def to_str(self):
        return self.proto + ' ' + self.type


class PCAP_Multicast(PCAP_PrimitiveCast):
    def __init__(self, proto='ether'):
        """
        :param proto: str Either 'ip' or 'ether' (default)
        """
        super(PCAP_Multicast, self).__init__('multicast', proto)


class PCAP_Broadcast(PCAP_PrimitiveCast):
    def __init__(self, proto='ether'):
        """
        :param proto: str Either 'ip' or 'ether' (default)
        """
        super(PCAP_Broadcast, self).__init__('broadcast', proto)


