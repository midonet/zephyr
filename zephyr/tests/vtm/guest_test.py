
import unittest


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


import os

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.vtm import neutron_api
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class GuestTest(unittest.TestCase):
    lm = None
    vtm = None
    api = None
    main_network = None
    main_subnet = None

    @classmethod
    def setUpClass(cls):
        cls.lm = LogManager('test-logs')
        cls.vtm = VirtualTopologyManager(
            client_api_impl=neutron_api.create_neutron_client())
        cls.vtm.configure_logging(debug=True)
        cls.vtm.read_underlay_config()
        cls.api = cls.vtm.get_client()
        """ :type: neutron_client.Client"""

        cls.main_network = cls.api.create_network(
            {'network': {
                'name': 'main',
                'tenant_id': 'admin'}})['network']
        cls.main_subnet = cls.api.create_subnet(
            {'subnet': {
                'name': 'main_sub',
                'ip_version': 4,
                'network_id': cls.main_network['id'],
                'cidr': '192.168.10.0/24',
                'tenant_id': 'admin'}})['subnet']

    def test_host_plugin_vm(self):
        vm = self.vtm.create_vm(name='vm1')
        port1def = {'port': {'name': 'port1',
                             'network_id': self.main_network['id'],
                             'admin_state_up': True,
                             'tenant_id': 'admin'}}
        port1 = self.api.create_port(port1def)['port']
        ip1 = port1['fixed_ips'][0]['ip_address']
        try:
            vm.plugin_vm('eth0', port1['id'])

            self.assertTrue(port1['id'] in vm.open_ports_by_id)

            vm.unplug_vm(port1['id'])

            self.assertFalse(port1['id'] in vm.open_ports_by_id)
        finally:
            if port1 is not None:
                self.api.delete_port(port1['id'])
            vm.terminate()

    def test_echo_server_tcp(self):
        vm1 = self.vtm.create_vm(name='vm1')

        try:
            vm1.start_echo_server(echo_data='test')
            ret = vm1.send_echo_request(echo_request='ping')
            self.assertEqual('ping:test', ret)

        finally:
            vm1.stop_echo_server()
            vm1.terminate()

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().cmd('ip netns del vm1')
        if cls.main_subnet:
            cls.api.delete_subnet(cls.main_subnet['id'])
        if cls.main_network:
            cls.api.delete_network(cls.main_network['id'])

run_unit_test(GuestTest)
