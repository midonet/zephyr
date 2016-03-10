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

from zephyr.common.exceptions import *


class Rule(object):
    def __init__(self):
        pass

    def to_str(self):
        raise ArgMismatchException(
            'All Rules should override the "to_str" method!')


class Simple(Rule):
    def __init__(self, val):
        """
        :param val: str
        """
        super(Simple, self).__init__()
        self.explicit_val = val

    def to_str(self):
        return self.explicit_val


class Null(Simple):
    def __init__(self):
        super(Null, self).__init__(val='')


class _PrimitiveBinaryBoolean(Rule):
    def __init__(self, operation, rule_set):
        """
        :param operation: str
        :param rule_set: list[PS_Rule]
        """
        super(_PrimitiveBinaryBoolean, self).__init__()
        self.operation = operation
        self.rule_set = rule_set

    def to_str(self):
        if len(self.rule_set) < 2:
            return ''.join(['( ' + i.to_str() + ' )' for i in self.rule_set])
        return (' ' + self.operation + ' ').join(['( ' + i.to_str() + ' )'
                                                  for i in self.rule_set])


class And(_PrimitiveBinaryBoolean):
    def __init__(self, rule_set):
        """
        :param rule_set: list[PS_Rule]
        """
        super(And, self).__init__('and', rule_set)


class Or(_PrimitiveBinaryBoolean):
    def __init__(self, rule_set):
        """
        :param rule_set: list[PS_Rule]
        """
        super(Or, self).__init__('or', rule_set)


class Not(Rule):
    def __init__(self, rule):
        """
        :param rule: PS_Rule
        """
        super(Not, self).__init__()
        self.rule = rule

    def to_str(self):
        return 'not ( ' + self.rule.to_str() + r' )'


class _PrimitiveComparison(Rule):
    def __init__(self, operation, lhs, rhs):
        """
        :param operation: str
        :param lhs: str
        :param rhs: str
        """
        super(_PrimitiveComparison, self).__init__()
        self.operation = operation
        self.lhs = lhs
        self.rhs = rhs

    def to_str(self):
        return str(self.lhs) + ' ' + str(self.operation) + ' ' + str(self.rhs)


class GreaterThanEqual(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(GreaterThanEqual, self).__init__('>=', lhs, rhs)


class GreaterThan(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(GreaterThan, self).__init__('>', lhs, rhs)


class Equal(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(Equal, self).__init__('=', lhs, rhs)


class NotEqual(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(NotEqual, self).__init__('!=', lhs, rhs)


class LessThan(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(LessThan, self).__init__('<', lhs, rhs)


class LessThanEqual(_PrimitiveComparison):
    def __init__(self, lhs, rhs):
        """
        :param lhs: str
        :param rhs: str
        """
        super(LessThanEqual, self).__init__('<=', lhs, rhs)


class _PrimitiveTypeRule(Rule):
    def __init__(self, param, proto='', source=False, dest=False):
        """
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(_PrimitiveTypeRule, self).__init__()
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


class Host(_PrimitiveTypeRule):
    def __init__(self, host, proto='', source=False, dest=False):
        """
        :param host: str
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(Host, self).__init__('host ' + host, proto, source, dest)


class PortRange(_PrimitiveTypeRule):
    def __init__(self, start_port, end_port, proto='',
                 source=False, dest=False):
        """
        :param start_port: int
        :param end_port: int
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(PortRange, self).__init__('portrange ' + str(start_port) +
                                        '-' + str(end_port),
                                        proto, source, dest)


class Port(_PrimitiveTypeRule):
    def __init__(self, port, proto='', source=False, dest=False):
        """
        :param port: int
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(Port, self).__init__('port ' + str(port), proto,
                                   source, dest)


class Net(_PrimitiveTypeRule):
    def __init__(self, net, mask='', proto='', source=False, dest=False):
        """
        :param net: str
        :param proto: str
        :param source: bool
        :param dest: bool
        """
        super(Net, self).__init__(
            'net ' + net + (' mask ' + mask if mask != '' else ''),
            proto, source, dest)


class _PrimitiveProtoRule(Rule):
    def __init__(self, base_proto, filter_proto):
        """
        :param base_proto: str Either 'ip' or 'ether'
        :param filter_proto: str For 'ip', can be 'tcp, icmp, udp'.  For
        'ether' can be 'ip', 'arp', 'stp'
        """
        super(_PrimitiveProtoRule, self).__init__()
        self.base_proto = base_proto
        self.filter_proto = filter_proto

    def to_str(self):
        return self.base_proto + ' proto ' + self.filter_proto


class IPProto(_PrimitiveProtoRule):
    def __init__(self, proto):
        """
        :param proto: str IP protocol value to check for
        """
        super(IPProto, self).__init__('ip', '\\' + proto)


class EtherProto(_PrimitiveProtoRule):
    def __init__(self, proto):
        """
        :param proto: str One of 'ip', 'arp', or 'stp'
        """
        super(EtherProto, self).__init__('ether', proto)


class _PrimitiveSimpleProto(Rule):
    def __init__(self, proto):
        """
        :param proto: str One of 'tcp', 'icmp', or 'udp'
        """
        super(_PrimitiveSimpleProto, self).__init__()
        self.proto = proto

    def to_str(self):
        return self.proto


class ICMPProto(_PrimitiveSimpleProto):
    def __init__(self):
        """
        """
        super(ICMPProto, self).__init__('icmp')


class TCPProto(_PrimitiveSimpleProto):
    def __init__(self):
        """
        """
        super(TCPProto, self).__init__('tcp')


class UDPProto(_PrimitiveSimpleProto):
    def __init__(self):
        """
        """
        super(UDPProto, self).__init__('udp')


class _PrimitiveCast(Rule):
    def __init__(self, ptype, proto='ether'):
        """
        :param ptype: str Either 'broadcast' or 'multicast'
        :param proto: str Either 'ip' or 'ether'
        """
        super(_PrimitiveCast, self).__init__()
        self.type = ptype
        self.proto = proto

    def to_str(self):
        return self.proto + ' ' + self.type


class Multicast(_PrimitiveCast):
    def __init__(self, proto='ether'):
        """
        :param proto: str Either 'ip' or 'ether' (default)
        """
        super(Multicast, self).__init__('multicast', proto)


class Broadcast(_PrimitiveCast):
    def __init__(self, proto='ether'):
        """
        :param proto: str Either 'ip' or 'ether' (default)
        """
        super(Broadcast, self).__init__('broadcast', proto)
