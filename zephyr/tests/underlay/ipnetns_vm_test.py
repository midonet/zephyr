
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

from zephyr.common import exceptions
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

    def setUp(self):
        self.vms = []
        self.ports = []
        self.networks = []
        self.subnets = []
        und_sys = self.vtm.underlay_system
        auth_type = und_sys.get_topology_feature("auth_type")
        self.api = None

        if auth_type == "keystone":
            self.api = neutron_api.create_neutron_client(
                auth_strategy='keystone',
                auth_url=os.environ.get('OS_ATUH_URL',
                                        'http://localhost:5000/v2.0'),
                username=os.environ.get('OS_USERNAME', 'admin'),
                password=os.environ.get('OS_PASSWORD', 'cat'),
                tenant_name=os.environ.get('OS_TENANT_NAME', 'admin'))
        elif auth_type == "noauth":
            self.api = neutron_api.create_neutron_client()
        else:
            raise exceptions.ArgMismatchException(
                "Unrecognized auth type '" + auth_type + "'")
        self.vtm.client_api_impl = self.api

    def test_vm_create(self):
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        self.assertIsNotNone(vm.get_hypervisor_name())

    def test_vm_create_on_host_as_single_string(self):
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)

        vm2 = self.vtm.create_vm(name='vm2',
                                 hv_host=vm.get_hypervisor_name())
        self.vms.append(vm2)
        self.assertEqual(vm.get_hypervisor_name(),
                         vm2.get_hypervisor_name())

    def test_vm_create_on_host_as_single_list(self):
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        vm2 = self.vtm.create_vm(name='vm2',
                                 hv_host=[vm.get_hypervisor_name()])
        self.vms.append(vm2)
        self.assertEqual(vm.get_hypervisor_name(),
                         vm2.get_hypervisor_name())

    def test_vm_create_on_host_as_multi_list(self):
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        vm2 = self.vtm.create_vm(name='vm2')
        self.vms.append(vm2)
        vm3 = self.vtm.create_vm(name='vm3',
                                 hv_host=[vm.get_hypervisor_name(),
                                          vm2.get_hypervisor_name()])
        self.vms.append(vm3)
        self.assertIn(vm3.get_hypervisor_name(),
                      [vm.get_hypervisor_name(),
                       vm2.get_hypervisor_name()])

    def test_vm_create_on_multi_host_natural_algorithm(self):
        und_sys = self.vtm.underlay_system
        if len(und_sys.hosts) < 2:
            unittest.skip("Need more than one host")
            return
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        vm2 = self.vtm.create_vm(name='vm2')
        self.vms.append(vm2)
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm2.get_hypervisor_name())

    def test_vm_create_not_on_host_list(self):
        und_sys = self.vtm.underlay_system
        if len(und_sys.hosts) < 2:
            unittest.skip("Need more than one host")
            return
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        vm2 = self.vtm.create_vm(name='vm2',
                                 hv_host=['!' + vm.get_hypervisor_name()])
        self.vms.append(vm2)
        vm3 = self.vtm.create_vm(name='vm3',
                                 hv_host=['!' + vm.get_hypervisor_name()])
        self.vms.append(vm3)
        vm4 = self.vtm.create_vm(name='vm4',
                                 hv_host=['!' + vm.get_hypervisor_name()])
        self.vms.append(vm4)
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm2.get_hypervisor_name())
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm3.get_hypervisor_name())
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm4.get_hypervisor_name())

    def test_vm_create_not_on_host_single_string(self):
        und_sys = self.vtm.underlay_system
        if len(und_sys.hosts) < 2:
            unittest.skip("Need more than one host")
            return
        vm = self.vtm.create_vm(name='vm1')
        self.vms.append(vm)
        vm2 = self.vtm.create_vm(name='vm2',
                                 hv_host='!' + vm.get_hypervisor_name())
        self.vms.append(vm2)
        vm3 = self.vtm.create_vm(name='vm3',
                                 hv_host='!' + vm.get_hypervisor_name())
        self.vms.append(vm3)
        vm4 = self.vtm.create_vm(name='vm4',
                                 hv_host='!' + vm.get_hypervisor_name())
        self.vms.append(vm4)
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm2.get_hypervisor_name())
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm3.get_hypervisor_name())
        self.assertNotEqual(vm.get_hypervisor_name(),
                            vm4.get_hypervisor_name())

    def test_vm_create_on_bad_host(self):
        try:
            vm = self.vtm.create_vm(
                name='vm2',
                hv_host=["no_way_this_compute_exists"])
            self.vms.append(vm)
            self.fail('This should throw ArgMismatchException')
        except exceptions.ArgMismatchException:
            pass

    def test_vm_create_not_on_any_host(self):
        try:
            vm = self.vtm.create_vm(
                name='vm2')
            self.vms.append(vm)
            vm2 = self.vtm.create_vm(
                name='vm2',
                hv_host=['!' + vm.get_hypervisor_name()])
            self.vms.append(vm2)
            vm3 = self.vtm.create_vm(
                name='vm3',
                hv_host=['!' + vm.get_hypervisor_name(),
                         '!' + vm2.get_hypervisor_name()])
            self.vms.append(vm3)
            vm4 = self.vtm.create_vm(
                name='vm4',
                hv_host=['!' + vm.get_hypervisor_name(),
                         '!' + vm2.get_hypervisor_name(),
                         '!' + vm3.get_hypervisor_name()])
            self.vms.append(vm4)
            vm5 = self.vtm.create_vm(
                name='vm5',
                hv_host=['!' + vm.get_hypervisor_name(),
                         '!' + vm2.get_hypervisor_name(),
                         '!' + vm3.get_hypervisor_name(),
                         '!' + vm4.get_hypervisor_name()])
            self.vms.append(vm5)
            self.fail('This should throw ObjectNotFoundException')
        except exceptions.ObjectNotFoundException:
            pass

    def test_vm_plugin_to_overlay(self):
        main_network = self.api.create_network(
            {'network': {
                'name': 'main',
                'tenant_id': 'admin'}})['network']
        self.networks.append(main_network)

        main_subnet = self.api.create_subnet(
            {'subnet': {
                'name': 'main_sub',
                'ip_version': 4,
                'network_id': main_network['id'],
                'cidr': '192.168.10.0/24',
                'tenant_id': 'admin'}})['subnet']
        self.subnets.append(main_subnet)
        port1def = {'port': {'name': 'port1',
                             'network_id': main_network['id'],
                             'admin_state_up': True,
                             'tenant_id': 'admin'}}
        port1 = self.api.create_port(port1def)['port']
        self.ports.append(port1)
        ip1 = port1['fixed_ips'][0]['ip_address']

        vm = self.vtm.create_vm(name='vm1',
                                mac=port1['mac_address'])
        self.vms.append(vm)
        vm.plugin_vm('eth0', port1['id'])
        vm.setup_vm_network(ip_addr=None,
                            gw_ip=main_subnet['gateway_ip'])

        self.assertEqual(ip1, vm.get_ip('eth0'))

    def test_vm_plugin_to_overlay_no_dhcp(self):
        main_network = self.api.create_network(
            {'network': {
                'name': 'main',
                'tenant_id': 'admin'}})['network']
        self.networks.append(main_network)
        main_subnet = self.api.create_subnet(
            {'subnet': {
                'name': 'main_sub',
                'ip_version': 4,
                'network_id': main_network['id'],
                'cidr': '192.168.10.0/24',
                'tenant_id': 'admin'}})['subnet']
        self.subnets.append(main_subnet)
        port1def = {'port': {'name': 'port1',
                             'network_id': main_network['id'],
                             'admin_state_up': True,
                             'tenant_id': 'admin'}}
        port1 = self.api.create_port(port1def)['port']
        self.ports.append(port1)
        ip1 = port1['fixed_ips'][0]['ip_address']

        vm = self.vtm.create_vm(
            name='vm1')
        self.vms.append(vm)
        vm.plugin_vm('eth0', port1['id'])
        vm.setup_vm_network(ip_addr=ip1,
                            gw_ip=main_subnet['gateway_ip'])

        self.assertEqual(ip1, vm.get_ip('eth0'))

    def test_vm_communication_direct(self):
        main_network = self.api.create_network(
            {'network': {
                'name': 'main',
                'tenant_id': 'admin'}})['network']
        self.networks.append(main_network)
        main_subnet = self.api.create_subnet(
            {'subnet': {
                'name': 'main_sub',
                'ip_version': 4,
                'network_id': main_network['id'],
                'cidr': '192.168.10.0/24',
                'tenant_id': 'admin'}})['subnet']
        self.subnets.append(main_subnet)

        port1def = {'port': {'name': 'port1',
                             'network_id': main_network['id'],
                             'admin_state_up': True,
                             'tenant_id': 'admin'}}
        port1 = self.api.create_port(port1def)['port']
        self.ports.append(port1)

        port2def = {'port': {'name': 'port2',
                             'network_id': main_network['id'],
                             'admin_state_up': True,
                             'tenant_id': 'admin'}}
        port2 = self.api.create_port(port2def)['port']
        self.ports.append(port2)

        vm1 = self.vtm.create_vm(name='vm1',
                                 mac=port1['mac_address'])
        self.vms.append(vm1)
        vm2 = self.vtm.create_vm(name='vm2',
                                 mac=port2['mac_address'])
        self.vms.append(vm2)

        vm1.plugin_vm('eth0', port1['id'])
        vm1.setup_vm_network(ip_addr=None,
                             gw_ip=main_subnet['gateway_ip'])

        vm2.plugin_vm('eth0', port2['id'])
        vm2.setup_vm_network(ip_addr=None,
                             gw_ip=main_subnet['gateway_ip'])

        self.assertTrue(vm1.verify_connection_to_host(vm2))

    def tearDown(self):
        for vm in self.vms:
            vm.terminate()
        for port in self.ports:
            self.api.delete_port(port['id'])
        for subnet in self.subnets:
            self.api.delete_subnet(subnet['id'])
        for network in self.networks:
            self.api.delete_network(network['id'])

run_unit_test(IPNetnsVMTest)
