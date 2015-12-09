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

from tests.scenarios.Scenario_Basic2ComputeWithEdge import Scenario_Basic2ComputeWithEdge
from TSM.NeutronTestCase import NeutronTestCase#, RouterData
from collections import namedtuple
from common.Exceptions import *
from common.IP import IP
import CBT.VersionConfig as version_config
import unittest

EdgeData = namedtuple('EdgeData', "network subnet router")
RouterData = namedtuple('RouterData', "router if_list")


class TestExternalPing(NeutronTestCase):

    @staticmethod
    def supported_scenarios():
        return {Scenario_Basic2ComputeWithEdge}

    @unittest.skipUnless(version_config.ConfigMap.get_configured_parameter('option_extension_extra_routes'),
                         'This test requires extra_routes extension in order to add default routes')
    def create_edge_router(self, edge_host='edge1', edge_iface='eth1',
                           edge_subnet='172.16.2.0/24'):

        # Create an uplink network (Midonet-specific extension used for provider:network_type)
        edge_network = self.api.create_network({'network': {'name': 'edge1',
                                                            'admin_state_up': True,
                                                            'provider:network_type': 'uplink',
                                                            'tenant_id': 'admin'}})['network']
        self.LOG.debug('Created edge network: ' + str(edge_network))

        # Create uplink network's subnet
        edge_ip = '.'.join(edge_subnet.split('.')[:-1]) + '.2'
        edge_gw = '.'.join(edge_subnet.split('.')[:-1]) + '.1'

        edge_subnet = self.api.create_subnet({'subnet': {'name': 'edge_sub',
                                                         'network_id': edge_network['id'],
                                                         'enable_dhcp': False,
                                                         'ip_version': 4,
                                                         'cidr': edge_subnet,
                                                         'tenant_id': 'admin'}})['subnet']
        self.LOG.debug('Created edge subnet: ' + str(edge_subnet))

        # Create edge router
        edge_router = self.api.create_router({'router': {'name': 'edge_router1',
                                                         'admin_state_up': True,
                                                         'tenant_id': 'admin'}})['router']
        self.LOG.debug('Created edge router: ' + str(edge_router))

        # Create "port" on router by creating a port on the special uplink network
        # bound to the physical interface on the physical host, and then linking
        # that network port to the router's interface.
        edge_port1 = self.api.create_port({'port': {'name': 'edge_port',
                                                    'network_id': edge_network['id'],
                                                    'admin_state_up': True,
                                                    'binding:host_id': edge_host,
                                                    'binding:profile': {'interface_name': edge_iface},
                                                    'fixed_ips': [{'subnet_id': edge_subnet['id'],
                                                                   'ip_address': edge_ip}],
                                                    'tenant_id': 'admin'}})['port']
        self.LOG.info('Created physical-bound, edge port: ' + str(edge_port1))
        # Bind port to edge router
        if1 = self.api.add_interface_router(edge_router['id'], {'port_id': edge_port1['id']})

        self.LOG.info('Added interface to edge router: ' + str(if1))

        # Bind public network to edge router
        if2 = self.api.add_interface_router(edge_router['id'], {'subnet_id': self.pub_subnet['id']})

        self.LOG.info('Added interface to edge router: ' + str(if2))

        # Add the default route
        edge_router = self.api.update_router(edge_router['id'],
                                             {'router': {'routes': [{'destination': '0.0.0.0/0',
                                                                     'nexthop': edge_gw}]}})['router']
        self.LOG.info('Added default route to edge router: ' + str(edge_router))

        router_host = self.ptm.impl_.hosts_by_name['router1']
        router_host.add_route(IP.make_ip(self.pub_subnet['cidr']), IP(edge_ip, '24'))
        self.LOG.info('Added return route to host router')

        return EdgeData(edge_network, edge_subnet, RouterData(edge_router, [if1, if2]))

    def delete_edge_router(self, edge_data):
        """
        :param edge_data: EdgeData
        :return:
        """
        # Create a public network
        if edge_data.router is not None:
            self.api.update_router(edge_data.router.router['id'], {'router': {'routes': None}})
            if edge_data.router.if_list is not None:
                for iface in edge_data.router.if_list:
                    self.api.remove_interface_router(edge_data.router.router['id'], iface)
            self.api.delete_router(edge_data.router.router['id'])
        if edge_data.subnet is not None:
            self.api.delete_subnet(edge_data.subnet['id'])
        if edge_data.network is not None:
            self.api.delete_network(edge_data.network['id'])

    def test_neutron_api_ping_external(self):
        port1 = None
        vm1 = None
        edge_data = self.create_edge_router()

        try:

            port1def = {'port': {'name': 'port1',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']
            self.LOG.info('Created port 1: ' + str(port1))

            self.LOG.info("Got VM1 IP: " + str(ip1))

            vm1 = self.vtm.create_vm(ip=ip1)

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])

            self.LOG.info('Pinging from VM1 to external')
            self.assertTrue(vm1.ping(target_ip='172.20.1.1', on_iface='eth0'))

        finally:
            if vm1 is not None:
                vm1.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])

            self.delete_edge_router(edge_data)

