__author__ = 'micucci'
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
        return IP(*ip_str.split('/'))

    def __str__(self):
        return self.ip + "/" + self.subnet

    def to_map(self):
        return {'ip': self.ip, 'subnet': self.subnet}


