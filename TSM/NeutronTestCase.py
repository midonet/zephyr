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
from collections import namedtuple

from TSM.TestCase import TestCase
from VTM.NeutronAPI import RouterData, NetData
from PTM.fixtures.MidonetHostSetupFixture import MidonetHostSetupFixture
from PTM.fixtures.NeutronDatabaseFixture import NeutronDatabaseFixture
from PTM.host.Host import Host
from VTM.MNAPI import create_midonet_client
from VTM.Guest import Guest
from common.IP import IP

import neutronclient.v2_0.client as neutron_client

GuestData = namedtuple('GuestData', 'port vm ip')
EdgeData = namedtuple('EdgeData', "edge_net router")


class NeutronTestCase(TestCase):

    def __init__(self, methodName='runTest'):
        super(NeutronTestCase, self).__init__(methodName)
        self.neutron_fixture = None
        """:type: NeutronDatabaseFixture"""
        self.midonet_fixture = None
        """:type: MidonetHostSetupFixture"""
        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet = None
        self.api = None
        """ :type: neutron_client.Client """
        self.mn_api = None

    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(NeutronTestCase, cls)._prepare_class(ptm, vtm, test_case_logger)

        cls.api = cls.vtm.get_client()
        """ :type: neutron_client.Client """
        cls.mn_api = create_midonet_client()

        ext_list = cls.api.list_extensions()['extensions']
        cls.api_extension_map = {v['alias']: v for v in ext_list}

        # Only add the midonet- and neutron-setup fixture once for each scenario.
        if 'midonet-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding midonet-setup fixture')
            midonet_fixture = MidonetHostSetupFixture(cls.vtm, cls.ptm, test_case_logger)
            ptm.add_fixture('midonet-setup', midonet_fixture)

        if 'neutron-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding neutron-setup fixture')
            neutron_fixture = NeutronDatabaseFixture(cls.vtm, cls.ptm, test_case_logger)
            ptm.add_fixture('neutron-setup', neutron_fixture)

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data prior to running
        the test case function.
        """
        self.neutron_fixture = self.ptm.get_fixture('neutron-setup')
        self.LOG.debug("Initializing Test Case Neutron Data from neutron-setup fixture")
        self.main_network = self.neutron_fixture.main_network
        self.main_subnet = self.neutron_fixture.main_subnet
        self.pub_network = self.neutron_fixture.pub_network
        self.pub_subnet = self.neutron_fixture.pub_subnet
        self.api = self.neutron_fixture.api
        self.mn_api = self.neutron_fixture.mn_api
        super(NeutronTestCase, self).run(result)

    #TODO: Change this to use the GuestData namedtuple
    def cleanup_vms(self, vm_port_list):
        """
        :type vm_port_list: list[(Guest, port)]
        """
        for vm, port in vm_port_list:
            try:
                self.LOG.debug('Shutting down vm on port: ' + str(port))
                if vm is not None:
                    vm.stop_capture(on_iface='eth0')
                    if port is not None:
                        vm.unplug_vm(port['id'])
                if port is not None:
                    self.api.delete_port(port['id'])
            finally:
                if vm is not None:
                    vm.terminate()

    def create_edge_router(self, pub_subnet=None, router_host_name='router1',
                           edge_host_name='edge1', edge_iface_name='eth1', edge_subnet_cidr='172.16.2.0/24'):

        if not pub_subnet:
            pub_subnet = self.pub_subnet

        # Create an uplink network (Midonet-specific extension used for provider:network_type)
        edge_network = self.api.create_network({'network': {'name': edge_host_name,
                                                            'admin_state_up': True,
                                                            'provider:network_type': 'uplink',
                                                            'tenant_id': 'admin'}})['network']
        self.LOG.debug('Created edge network: ' + str(edge_network))

        # Create uplink network's subnet
        edge_ip = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.2'
        edge_gw = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.1'

        edge_subnet = self.api.create_subnet({'subnet': {'name': edge_host_name + '_sub',
                                                         'network_id': edge_network['id'],
                                                         'enable_dhcp': False,
                                                         'ip_version': 4,
                                                         'cidr': edge_subnet_cidr,
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
        edge_port1 = self.api.create_port({'port': {'name': edge_host_name + '_port',
                                                    'network_id': edge_network['id'],
                                                    'admin_state_up': True,
                                                    'binding:host_id': edge_host_name,
                                                    'binding:profile': {'interface_name': edge_iface_name},
                                                    'fixed_ips': [{'subnet_id': edge_subnet['id'],
                                                                   'ip_address': edge_ip}],
                                                    'tenant_id': 'admin'}})['port']
        self.LOG.info('Created physical-bound, edge port: ' + str(edge_port1))
        # Bind port to edge router
        if1 = self.api.add_interface_router(edge_router['id'], {'port_id': edge_port1['id']})

        self.LOG.info('Added interface to edge router: ' + str(if1))

        # Bind public network to edge router
        if2 = self.api.add_interface_router(edge_router['id'], {'subnet_id': pub_subnet['id']})

        self.LOG.info('Added interface to edge router: ' + str(if2))

        # Add the default route
        edge_router = self.api.update_router(edge_router['id'],
                                             {'router': {'routes': [{'destination': '0.0.0.0/0',
                                                                     'nexthop': edge_gw}]}})['router']
        self.LOG.info('Added default route to edge router: ' + str(edge_router))

        router_host = self.ptm.impl_.hosts_by_name[router_host_name]
        """ :type: Host"""
        router_host.add_route(IP.make_ip(pub_subnet['cidr']), IP(edge_ip, '24'))
        self.LOG.info('Added return route to host router')

        return EdgeData(NetData(edge_network, edge_subnet), RouterData(edge_router, [if1, if2]))

    def delete_edge_router(self, edge_data):
        """
        :type edge_data: EdgeData
        :return:
        """
        # Create a public network
        if edge_data:
            if edge_data.router:
                self.api.update_router(edge_data.router.router['id'], {'router': {'routes': None}})
                if edge_data.router.if_list:
                    for iface in edge_data.router.if_list:
                        self.api.remove_interface_router(edge_data.router.router['id'], iface)
                self.api.delete_router(edge_data.router.router['id'])
            if edge_data.edge_net.subnet:
                self.api.delete_subnet(edge_data.edge_net.subnet['id'])
            if edge_data.edge_net.network:
                self.api.delete_network(edge_data.edge_net.network['id'])


class require_extension(object):
    def __init__(self, ext):
        self.ext = ext

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :param slf: TestCase
            """
            if self.ext in slf.api_extension_map:
                f(slf, *args)
            else:
                slf.skipTest('Skipping because extension: ' + str(self.ext) + ' is not installed')
        return new_tester
