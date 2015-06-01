__author__ = 'micucci'

import unittest
from datetime import datetime

from VTM.Guest import Guest
from VTM.VirtualTopologyConfig import VirtualTopologyConfig
from PTM.VMHost import VMHost
from PTM.ComputeHost import ComputeHost
from PTM.PhysicalTopologyConfig import *
from PTM.MNRootServer import MNRootServer
from VTM.Network import Network
from VTM.Port import Port


class MockNetwork(Network):
    def __init__(self, vtc):
        super(MockNetwork, self).__init__(vtc)




class MockClient(object):
    gid=0

    def __init__(self, *args, **kwargs):
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

    def create_port(self):
        obj_map = {'name': 'test' + str(MockClient.gid),
                   'id': str(MockClient.gid),
                   'network_id': me.network_id,
                   'admin_state_up': True,
                   'status': me.status,
                   'mac_address': me.mac_address,
                   'fixed_ips': me.fixed_ips,
                   'device_id': me.device_id,
                   'device_owner': me.device_owner}
        port = None
        port_id = "fe6707e3-9c99-4529-b059-aa669d1463bb"
        self.ports[port_id] = port
        return port_id

    def create_network(self, options):
        data = options['network']
        return {'network': {'name': data['name'], 'tenant_id': data['tenant_id'], 'id': 'mock-id'}}

    def create_subnet(self, options):
        data = options['network']
        return {'subnet': {'name': data['name'],
                           'tenant_id': data['tenant_id'],
                           'cidr':'1.1.1.0/24',
                           'network_id': data['id'],
                           'ip_version': 4}}

    def create_port(self, options):
        return {'port': {'tenant_id': tenant_id,
          'network_id': network_id}}


class MyTestCase(unittest.TestCase):

    def test_ping_between_two_hosts(self):
        vtc = VirtualTopologyConfig(client_api_impl=MockClient)

        test_system = MNRootServer()
        hv = test_system.config_compute(HostDef('cmp1', [InterfaceDef(name='eth0', ip_list=[IPDef('2.2.2.2', '32')])]))
        vm = test_system.config_vm(VMDef('cmp1', HostDef('vm1', [InterfaceDef(name='eth0',
                                                                         ip_list=[IPDef('3.3.3.3', '32')])])))

        virtual_host = Guest(vtc,vtc)

        port = Port.from_json(vtc.get_client().create_port())
        """ :type: Port """

        virtual_host.plugin_vm(hv.get_interfaces_for_host('vm1')['eth0'], port_id)

        tenant_id = 'mdts2_test_ping_between_two_vms' + \
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        name = 'test_ping_between_two_vms'

        #
        # Topology setup
        #

        # create network and subnet
        net_data = {'name': name, 'tenant_id': tenant_id}
        net = Network.from_json(vtc.get_client().create_network({'network':net_data}))
        """ :type: Network """

        network_id = net['network']['id']

        subnet = Subnet.from_json(vtc.client_api_impl.create_subnet(net))

        # create two ports
        port1 = vtc.client_api_impl.create_port({'port':net_data}))

        port2 = vtc.client_api_impl.create_port(
            {'port': {'tenant_id': tenant_id,
                      'network_id': network_id}})

        # create two VMs on host[0] for each port
        vm1 = self.hosts[0].create_vm('vm1', port1)
        vm2 = self.hosts[0].create_vm('vm2', port2)

        # Test:
        # make sure that vm1 cna vm2 can ping each other
        #
        vm1.assert_pings_to(vm2)
        vm2.assert_pings_to(vm1)

        #
        # teardown VMs and neutron
        #
        vm1.delete()
        vm2.delete()

        # tearing down neutron ports and network
        self.neutron_client.delete_port(port1['port']['id'])
        self.neutron_client.delete_port(port2['port']['id'])
        self.neutron_client.delete_network(network_id)


if __name__ == '__main__':
    unittest.main()
