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

from TSM.NeutronTestCase import NeutronTestCase
from tests.scenarios.Secnario_1z_1c_2m import Secnario_1z_1c_2m
from VTM.Guest import Guest

from  collections import namedtuple

TopoData = namedtuple('TopoData',
                      'net1 net2 subnet1 subnet2 port1 port2 if1 if2 router1')

class TestExtraRoutes(NeutronTestCase):
    @staticmethod
    def supported_scenarios():
        return {Secnario_1z_1c_2m}

    def setup_standard_neutron_topo(self):
        try:
            net1def = {'network': {'name': 'net1', 'admin_state_up': True,
                                   'tenant_id': 'admin'}}
            net2def = {'network': {'name': 'net2', 'admin_state_up': True,
                                   'tenant_id': 'admin'}}

            net1 = self.api.create_network(net1def)['network']
            self.LOG.debug('Created net1: ' + str(net1))

            net2 = self.api.create_network(net2def)['network']
            self.LOG.debug('Created net2: ' + str(net2))

            subnet1def = {'subnet': {'name': 'net1_sub',
                                     'network_id': net1['id'],
                                     'ip_version': 4, 'cidr': '192.168.1.0/24',
                                     'tenant_id': 'admin'}}
            subnet2def = {'subnet': {'name': 'net2_sub',
                                     'network_id': net2['id'],
                                     'ip_version': 4, 'cidr': '192.168.2.0/24',
                                     'tenant_id': 'admin'}}

            subnet1 = self.api.create_subnet(subnet1def)['subnet']
            self.LOG.debug('Created subnet1: ' + str(subnet1))

            subnet2 = self.api.create_subnet(subnet2def)['subnet']
            self.LOG.debug('Created subnet2: ' + str(subnet2))

            router1def = {'router': {
                'name': 'router1to2',
                'admin_state_up': True,
                'external_gateway_info': {
                    "network_id": self.pub_network['id']
                },
                'tenant_id': 'admin'
            }}

            router1 = self.api.create_router(router1def)['router']
            self.LOG.debug('Created router1 from net1 to net2: ' + str(router1))

            port1def = {'port': {'name': 'port1',
                                 'network_id': net1['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2def = {'port': {'name': 'port2',
                                 'network_id': net2['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            self.LOG.debug('Created port2: ' + str(port2))

            if1def = {'subnet_id': subnet1['id']}
            if2def = {'subnet_id': subnet2['id']}

            if1 = self.api.add_interface_router(router1['id'], if1def)
            if2 = self.api.add_interface_router(router1['id'], if2def)

            self.LOG.debug("Added interface to router: " + str(if1))
            self.LOG.debug("Added interface to router: " + str(if2))

            return TopoData(net1, net2, subnet1, subnet2, port1, port2, if1, if2, router1)
        except Exception as e:
            self.LOG.fatal('Error setting up topology: ' + str(e))
            raise e

    def clear_neutron_topo(self, td):
        """
        :type td: TopoData
        :return:
        """
        if td is None:
            return
        if td.router1 is not None:
            self.api.update_router(td.router1['id'], {'router': {'routes': None}})
        if td.if1 is not None:
            self.api.remove_interface_router(td.router1['id'], td.if1)
        if td.if2 is not None:
            self.api.remove_interface_router(td.router1['id'], td.if2)
        if td.router1 is not None:
            self.api.delete_router(td.router1['id'])
        if td.port1 is not None:
            self.api.delete_port(td.port1['id'])
        if td.port2 is not None:
            self.api.delete_port(td.port2['id'])
        if td.subnet1 is not None:
            self.api.delete_subnet(td.subnet1['id'])
        if td.subnet2 is not None:
            self.api.delete_subnet(td.subnet2['id'])
        if td.net1 is not None:
            self.api.delete_network(td.net1['id'])
        if td.net2 is not None:
            self.api.delete_network(td.net2['id'])

    def test_extra_routes_1R2SN_multi_ip_interface_ping_same_hv(self):
        vm1 = None
        vm2 = None
        td = None
        try:
            td = self.setup_standard_neutron_topo()

            ip1 = td.port1['fixed_ips'][0]['ip_address']
            ip2 = td.port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=td.subnet1['gateway_ip'], preferred_hv_host='cmp2')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=td.subnet2['gateway_ip'], preferred_hv_host='cmp2')
            """ :type: Guest"""

            vm1.plugin_vm('eth0', td.port1['id'], td.port1['mac_address'])
            vm2.plugin_vm('eth0', td.port2['id'], td.port2['mac_address'])

            # Add an extra IP addr to vm1's interface
            vm1.execute('ip a add 172.16.0.2/32 dev eth0')

            # Add extra route for router to route 172.16.0.2 to subnet1
            updatedef = {'router': {
                'routes': [
                    {
                        'destination': '172.16.0.2/32',
                        'nexthop': ip1
                    }
                ]
            }}
            new_router1 = self.api.update_router(td.router1['id'], updatedef)['router']

            # Re-assign named tuple with "router1" field set to new value (must reset because
            #   named tuples are immutable).
            self.LOG.debug('Added extra route to router: ' + str(new_router1))
            td = TopoData(**{f: (v if f != 'router1' else new_router1) for f, v in td._asdict().iteritems()})

            self.LOG.info('Pinging from VM1 to VM2')
            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            self.LOG.info('Pinging from VM2 to VM1')
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip=ip1))

            self.LOG.info("Pinging from VM2 to VM1's extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.16.0.2'))

        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()
            self.clear_neutron_topo(td)

    def test_extra_routes_1R2SN_multi_ip_interface_ping_diff_hv(self):
        vm1 = None
        vm2 = None
        td = None
        try:
            td = self.setup_standard_neutron_topo()

            ip1 = td.port1['fixed_ips'][0]['ip_address']
            ip2 = td.port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=td.subnet1['gateway_ip'], preferred_hv_host='cmp2')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=td.subnet2['gateway_ip'], preferred_hv_host='cmp1')
            """ :type: Guest"""

            vm1.plugin_vm('eth0', td.port1['id'], td.port1['mac_address'])
            vm2.plugin_vm('eth0', td.port2['id'], td.port2['mac_address'])

            # Add an extra IP addr to vm1's interface
            vm1.execute('ip a add 172.16.0.2/32 dev eth0')

            # Add extra route for router to route 172.16.0.2 to subnet1
            updatedef = {'router': {
                'routes': [
                    {
                        'destination': '172.16.0.2/32',
                        'nexthop': ip1
                    }
                ]
            }}
            new_router1 = self.api.update_router(td.router1['id'], updatedef)['router']

            # Re-assign named tuple with "router1" field set to new value (must reset because
            #   named tuples are immutable).
            self.LOG.debug('Added extra route to router: ' + str(new_router1))
            td = TopoData(**{f: (v if f != 'router1' else new_router1) for f, v in td._asdict().iteritems()})

            self.LOG.info('Pinging from VM1 to VM2')
            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            self.LOG.info('Pinging from VM2 to VM1')
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip=ip1))

            self.LOG.info("Pinging from VM2 to VM1's extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.16.0.2'))

        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()
            self.clear_neutron_topo(td)

    def test_extra_routes_1R2SN_multi_ip_interface_ping_outside(self):
        # skip for now
        """
        vm1 = None
        vm2 = None
        td = None
        try:
            td = self.setup_standard_neutron_topo()

            ip1 = td.port1['fixed_ips'][0]['ip_address']
            ip2 = td.port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=td.subnet1['gateway_ip'], preferred_hv_host='cmp2')
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=td.subnet2['gateway_ip'], preferred_hv_host='cmp1')

            vm1.plugin_vm('eth0', td.port1['id'], td.port1['mac_address'])
            vm2.plugin_vm('eth0', td.port2['id'], td.port2['mac_address'])

            # Add an extra IP addr to vm1's interface
            vm1.execute('ip a add 172.16.0.2/32 dev eth0')

            # Add extra route for router to route 172.16.0.2 to subnet1
            updatedef = {'router': {
                'routes': [
                    {
                        'destination': '172.16.0.2/32',
                        'nexthop': ip1
                    }
                ]
            }}
            new_router1 = self.api.update_router(td.router1['id'], updatedef)['router']

            # Re-assign named tuple with "router1" field set to new value (must reset because
            #   named tuples are immutable).
            self.LOG.debug('Added extra route to router: ' + str(new_router1))
            td = TopoData(**{f: (v if f != 'router1' else new_router1) for f, v in td._asdict().iteritems()})

            self.LOG.info('Pinging from VM1 to 8.8.8.8')
            self.assertTrue(vm1.ping(on_iface='eth0', target_ip="8.8.8.8"))

            self.LOG.info('Pinging from VM2 to 8.8.8.8')
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip="8.8.8.8"))

        finally:
            raw_input("Pausing...")
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()
            self.clear_neutron_topo(td)
        """

    def test_extra_routes_1R2SN_multi_ip_interface_multiple_routes(self):
        vm1 = None
        vm2 = None
        td = None
        try:
            td = self.setup_standard_neutron_topo()

            ip1 = td.port1['fixed_ips'][0]['ip_address']
            ip2 = td.port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=td.subnet1['gateway_ip'], preferred_hv_host='cmp2')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=td.subnet2['gateway_ip'], preferred_hv_host='cmp1')
            """ :type: Guest"""

            vm1.plugin_vm('eth0', td.port1['id'], td.port1['mac_address'])
            vm2.plugin_vm('eth0', td.port2['id'], td.port2['mac_address'])

            # Add two extra IP addrs to vm1's interface and one to vm2
            vm1.execute('ip a add 172.16.0.2/32 dev eth0')
            vm1.execute('ip a add 172.17.0.2/32 dev eth0')
            vm2.execute('ip a add 172.18.0.2/32 dev eth0')

            # Add extra route for router to route 172.16.0.2 to subnet1
            updatedef = {'router': {
                'routes': [
                    {
                        'destination': '172.16.0.2/32',
                        'nexthop': ip1
                    },
                    {
                        'destination': '172.17.0.2/32',
                        'nexthop': ip1
                    },
                    {
                        'destination': '172.18.0.2/32',
                        'nexthop': ip2
                    }
                ]
            }}
            new_router1 = self.api.update_router(td.router1['id'], updatedef)['router']

            # Re-assign named tuple with "router1" field set to new value (must reset because
            #   named tuples are immutable).
            self.LOG.debug('Added extra route to router: ' + str(new_router1))
            td = TopoData(**{f: (v if f != 'router1' else new_router1) for f, v in td._asdict().iteritems()})

            self.LOG.info('Pinging from VM1 to VM2')
            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            self.LOG.info('Pinging from VM2 to VM1')
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip=ip1))

            self.LOG.info("Pinging from VM2 to VM1's first extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.16.0.2'))

            self.LOG.info("Pinging from VM2 to VM1's second extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.17.0.2'))

            self.LOG.info("Pinging from VM1 to VM2's extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.18.0.2'))

        finally:
            self.cleanup_vms([(vm1, None), (vm2, None)])
            self.clear_neutron_topo(td)

    def test_extra_routes_1R2SN_multi_ip_interface_ping_subnet_route(self):
        vm1 = None
        vm2 = None
        td = None
        try:
            td = self.setup_standard_neutron_topo()

            ip1 = td.port1['fixed_ips'][0]['ip_address']
            ip2 = td.port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=td.subnet1['gateway_ip'], preferred_hv_host='cmp2')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=td.subnet2['gateway_ip'], preferred_hv_host='cmp1')
            """ :type: Guest"""

            vm1.plugin_vm('eth0', td.port1['id'], td.port1['mac_address'])
            vm2.plugin_vm('eth0', td.port2['id'], td.port2['mac_address'])

            # Add an extra IP addr to vm1's interface
            vm1.execute('ip a add 172.16.0.2/32 dev eth0')
            # Add another extra IP addr to vm1's interface
            vm1.execute('ip a add 172.16.0.3/32 dev eth0')

            # Add extra route for router to route 172.16.0.2 to subnet1
            updatedef = {'router': {
                'routes': [
                    {
                        'destination': '172.16.0.0/24',
                        'nexthop': ip1
                    }
                ]
            }}
            new_router1 = self.api.update_router(td.router1['id'], updatedef)['router']

            # Re-assign named tuple with "router1" field set to new value (must reset because
            #   named tuples are immutable).
            self.LOG.debug('Added extra route to router: ' + str(new_router1))
            td = TopoData(**{f: (v if f != 'router1' else new_router1) for f, v in td._asdict().iteritems()})

            self.LOG.info('Pinging from VM1 to VM2')
            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            self.LOG.info('Pinging from VM2 to VM1')
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip=ip1))

            self.LOG.info("Pinging from VM2 to VM1's first extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.16.0.2'))

            self.LOG.info("Pinging from VM2 to VM1's second extra address")
            self.assertTrue(vm2.ping(on_iface='eth0', target_ip='172.16.0.3'))

        finally:
            self.cleanup_vms([(vm1, None), (vm2, None)])
            self.clear_neutron_topo(td)

