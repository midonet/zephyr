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

import unittest

from zephyr.common.utils import run_unit_test
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager


class MockClient(object):
    def __init__(self, **kwargs):
        super(MockClient, self).__init__()
        self.subnet = {}
        self.options = {}
        if kwargs is not None:
            for k, v in kwargs.iteritems():
                self.options[k] = v
        pass

    def list_ports(self):
        pass

    def list_networks(self):
        pass

    def delete_port(self, port):
        pass

    def delete_network(self, network):
        pass

    def set_subnet(self, subnet):
        self.subnet = subnet

    def show_subnet(self):
        return self.subnet

    def get_option(self, key):
        if key in self.options:
            return self.options[key]
        return None


class VirtualTopologyManagerUnitTest(unittest.TestCase):
    def test_creation(self):
        api = VirtualTopologyManager(
            client_api_impl=MockClient(endpoint_url='test',
                                       auth_strategy='test2',
                                       option1='test3'))

        self.assertEqual(api.get_client().get_option('endpoint_url'), 'test')
        self.assertEqual(api.get_client().get_option('auth_strategy'), 'test2')
        self.assertEqual(api.get_client().get_option('option1'), 'test3')

    def test_subnet(self):
        api = VirtualTopologyManager(client_api_impl=MockClient())
        subnet = {
            'subnet': {
                'name': 'test-l2',
                'enable_dhcp': True,
                'network_id': 'b6c86193-024c-4aeb-bd9c-ffc747bb8a74',
                'tenant_id': 'mdts2-ft2015-03-10 06:03:17',
                'dns_nameservers': [],
                'ipv6_ra_mode': None,
                'allocation_pools': [
                    {
                        'start': '1.1.1.2',
                        'end': '1.1.1.254'}],
                'gateway_ip': '1.1.1.1',
                'ipv6_address_mode': None,
                'ip_version': 4,
                'host_routes': [],
                'cidr': '1.1.1.0/24',
                'id': '6c838ffc-6a40-49ba-b363-6380b0a7dae6'}}

        api.get_client().set_subnet(subnet)
        self.assertEqual(api.get_client().show_subnet(), subnet)


run_unit_test(VirtualTopologyManagerUnitTest)
