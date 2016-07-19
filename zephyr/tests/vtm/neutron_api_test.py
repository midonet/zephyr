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

import logging
import os
import unittest

from zephyr.common.cli import LinuxCLI
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test
from zephyr.common import zephyr_constants as z_con
from zephyr.vtm import neutron_api
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class NeutronAPITest(unittest.TestCase):
    lm = LogManager('test-logs')
    vtm = None
    api = None
    mn_api = None
    main_network = None
    main_subnet = None
    pub_network = None
    pub_subnet = None
    public_router = None
    public_router_iface = None

    def setUp(self):
        logging.getLogger("neutronclient").addHandler(logging.StreamHandler())
        try:
            self.vtm = VirtualTopologyManager(
                client_api_impl=neutron_api.create_neutron_client())
            self.vtm.configure_logging(debug=True)
            self.vtm.read_underlay_config(z_con.DEFAULT_UNDERLAY_CONFIG)
            self.api = self.vtm.get_client()
            """ :type: neutron_client.Client"""

            self.main_network = self.api.create_network(
                {'network': {
                    'name': 'main',
                    'tenant_id': 'admin'}})['network']
            self.main_subnet = self.api.create_subnet(
                {'subnet': {
                    'name': 'main_sub',
                    'ip_version': 4,
                    'network_id': self.main_network['id'],
                    'cidr': '192.168.10.0/24',
                    'tenant_id': 'admin'}})['subnet']
            self.pub_network = self.api.create_network(
                {'network': {
                    'name': 'public',
                    'router:external': True,
                    'tenant_id': 'admin'}})['network']
            self.pub_subnet = self.api.create_subnet(
                {'subnet': {
                    'name': 'public_sub',
                    'ip_version': 4,
                    'network_id': self.pub_network['id'],
                    'cidr': '200.200.10.0/24',
                    'tenant_id': 'admin'}})['subnet']
            self.public_router = self.api.create_router(
                {'router': {
                    'name': 'main_public_router',
                    'external_gateway_info': {
                        'network_id': self.pub_network['id']},
                    'tenant_id': 'admin'}})['router']
            self.public_router_iface = self.api.add_interface_router(
                self.public_router['id'],
                {'subnet_id': self.main_subnet['id']})

        except (KeyboardInterrupt, Exception):
            LinuxCLI().cmd('ip netns del vm1')
            raise

    def test_neutron_api_ping_two_hosts_same_hv(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None

        try:
            port1def = {'port': {'name': 'port1',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.vtm.LOG.info("Got port 1 IP: " + str(ip1))
            self.vtm.LOG.info("Got port 2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(mac=port1['mac_address'])
            vm2 = self.vtm.create_vm(mac=port2['mac_address'],
                                     hv_host=vm1.get_hypervisor_name())

            vm1.plugin_vm('eth0', port1['id'])
            vm1.setup_vm_network()
            vm2.plugin_vm('eth0', port2['id'])
            vm2.setup_vm_network()

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))
        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])
            if port2 is not None:
                self.api.delete_port(port2['id'])

    def test_neutron_api_ping_two_hosts_diff_hv(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None

        try:
            port1def = {'port': {'name': 'port1',
                                 'network_id': self.pub_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.pub_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.vtm.LOG.info("Got port 1 IP: " + str(ip1))
            self.vtm.LOG.info("Got port 2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(mac=port1['mac_address'],
                                     name='vm1')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(mac=port2['mac_address'],
                                     name='vm2',
                                     hv_host='!' + vm1.get_hypervisor_name())
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm1.setup_vm_network()
            vm2.plugin_vm('eth0', port2['id'])
            vm2.setup_vm_network()
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])
            if port2 is not None:
                self.api.delete_port(port2['id'])

    def tearDown(self):
        if self.public_router:
            if self.public_router_iface:
                self.api.remove_interface_router(self.public_router['id'],
                                                 self.public_router_iface)
            self.api.delete_router(self.public_router['id'])
        if self.main_subnet:
            self.api.delete_subnet(self.main_subnet['id'])
        if self.pub_subnet:
            self.api.delete_subnet(self.pub_subnet['id'])
        if self.main_network:
            self.api.delete_network(self.main_network['id'])
        if self.pub_network:
            self.api.delete_network(self.pub_network['id'])

        LinuxCLI().cmd('ip netns del vm1')


run_unit_test(NeutronAPITest)
