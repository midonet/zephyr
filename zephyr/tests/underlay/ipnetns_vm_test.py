
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

from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.vtm import neutron_api
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class IPNetnsVMTest(unittest.TestCase):
    lm = None
    vtm = None

    @classmethod
    def setUpClass(cls):
        cls.lm = LogManager('test-logs')
        cls.vtm = VirtualTopologyManager(log_manager=cls.lm)
        cls.vtm.configure_logging(debug=True)
        cls.vtm.read_underlay_config()

    def test_vm_create(self):
        und_sys = self.vtm.underlay_system
        und_type = und_sys.get_topology_feature("underlay_type")
        if und_type != "direct":
            unittest.skip("Not on a direct underlay")
        vm = self.vtm.create_vm(name='vm1', ip_addr="10.3.3.3")
        vm.terminate()
        self.assertTrue(True)

    def test_vm_plugin_to_overlay(self):
        und_sys = self.vtm.underlay_system
        und_type = und_sys.get_topology_feature("underlay_type")
        if und_type != "direct":
            unittest.skip("Not on a direct underlay")

        api = neutron_api.create_neutron_client(
            auth_strategy='keystone',
            auth_url=os.environ.get('OS_ATUH_URL',
                                    'http://localhost:5000/v2.0'),
            username=os.environ.get('OS_USERNAME', 'admin'),
            password=os.environ.get('OS_PASSWORD', 'cat'),
            tenant_name=os.environ.get('OS_TENANT_NAME', 'admin'))
        """ :type: neutronclient.v2_0.client.Client"""
        self.vtm.client_api_impl = api

        vm = None

        main_network = None
        main_subnet = None
        port1 = None
        try:
            main_network = api.create_network(
                {'network': {
                    'name': 'main',
                    'tenant_id': 'admin'}})['network']
            main_subnet = api.create_subnet(
                {'subnet': {
                    'name': 'main_sub',
                    'ip_version': 4,
                    'network_id': main_network['id'],
                    'cidr': '192.168.10.0/24',
                    'tenant_id': 'admin'}})['subnet']
            port1def = {'port': {'name': 'port1',
                                 'network_id': main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm = self.vtm.create_vm(
                name='vm1', ip_addr=ip1,
                gw_ip=main_subnet['gateway_ip'])
            vm.plugin_vm('eth0', port1['id'])
            self.assertTrue(True)
        finally:
            if port1:
                api.delete_port(port1['id'])
            if main_subnet:
                api.delete_subnet(main_subnet['id'])
            if main_network:
                api.delete_network(main_network['id'])
            if vm:
                vm.terminate()

    def test_vm_communication(self):
        und_sys = self.vtm.underlay_system
        und_type = und_sys.get_topology_feature("underlay_type")
        if und_type != "direct":
            unittest.skip("Not on a direct underlay")

        api = neutron_api.create_neutron_client(
            auth_strategy='keystone',
            auth_url=os.environ.get('OS_ATUH_URL',
                                    'http://localhost:5000/v2.0'),
            username=os.environ.get('OS_USERNAME', 'admin'),
            password=os.environ.get('OS_PASSWORD', 'cat'),
            tenant_name=os.environ.get('OS_TENANT_NAME', 'admin'))
        """ :type: neutronclient.v2_0.client.Client"""
        self.vtm.client_api_impl = api

        vm1 = None
        vm2 = None

        main_network = None
        main_subnet = None
        port1 = None
        port2 = None
        try:
            main_network = api.create_network(
                {'network': {
                    'name': 'main',
                    'tenant_id': 'admin'}})['network']
            main_subnet = api.create_subnet(
                {'subnet': {
                    'name': 'main_sub',
                    'ip_version': 4,
                    'network_id': main_network['id'],
                    'cidr': '192.168.10.0/24',
                    'tenant_id': 'admin'}})['subnet']

            port1def = {'port': {'name': 'port1',
                                 'network_id': main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2def = {'port': {'name': 'port2',
                                 'network_id': main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(name='vm1', ip_addr=ip1,
                                     mac=port1['mac_address'],
                                     gw_ip=main_subnet['gateway_ip'])
            vm2 = self.vtm.create_vm(name='vm2', ip_addr=ip2,
                                     mac=port2['mac_address'],
                                     gw_ip=main_subnet['gateway_ip'])

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])
            self.assertTrue(vm1.ping(target_ip=ip2, timeout=30))

        finally:
            if port1:
                api.delete_port(port1['id'])
            if port2:
                api.delete_port(port2['id'])
            if main_subnet:
                api.delete_subnet(main_subnet['id'])
            if main_network:
                api.delete_network(main_network['id'])
            if vm1:
                vm1.terminate()
            if vm2:
                vm2.terminate()

run_unit_test(IPNetnsVMTest)
