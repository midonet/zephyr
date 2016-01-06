# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from common.Exceptions import *


class IP(object):
    def __init__(self, ip='0.0.0.0', subnet='24'):
        """
        :type ip: str
        :type subnet: str
        """
        self.ip = ip
        self.subnet = subnet

    @staticmethod
    def make_ip(ip_str):
        """
        Create an IP object from a string
        :param ip_str: str IP in dotted address CIDR notation (with optional '/' + subnet mask)
        :return: IP
        """
        return IP(*ip_str.split('/'))

    def __str__(self):
        return self.ip + "/" + self.subnet

    def to_map(self):
        return {'ip': self.ip, 'subnet': self.subnet}

    @staticmethod
    def from_map(map):
        if not 'ip' in map:
            raise ArgMismatchException('Expected "ip" member in IP map')
        if not 'subnet' in map:
            raise ArgMismatchException('Expected "subnet" member in IP map')

        return IP(map['ip'], map['subnet'])

    @staticmethod
    def ip_regex():
        return (r'(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}'
                r'([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])')
