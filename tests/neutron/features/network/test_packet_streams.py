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

from PTM.host.Host import Host

from TSM.NeutronTestCase import NeutronTestCase, require_extension
from TSM.TestCase import expected_failure
from VTM.NeutronAPI import create_neutron_main_pub_networks, delete_neutron_main_pub_networks
from VTM.Guest import Guest

PACKETS_TO_SEND_SHORT = 20
PACKETS_TO_SEND_MEDIUM = 100
PACKETS_TO_SEND_LONG = 3000


class TestPacketStreams(NeutronTestCase):
    """
    Test large packet streams and flows between nodes with streams consisting of
    dozens, hundreds, and even thousands of packets
    """

    def create_vms_and_stream_packets(self, num_packets, vm1_net, vm1_subnet, vm2_net, vm2_subnet):
        # Allowed address pair must have IP address
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': vm1_net['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']
            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], gw_ip=vm1_subnet['gateway_ip'])
            """ :type: Guest"""

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': vm2_net['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], gw_ip=vm2_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            responses = 0
            vm2.start_echo_server(ip=ip2)
            self.LOG.debug("Sending" + str(num_packets) + " packets to " + str(ip2))
            for i in range(0, num_packets):
                echo_response = vm1.send_echo_request(dest_ip=ip2)
                if echo_response == 'ping:echo-reply':
                    responses += 1

            self.assertEqual(num_packets, responses)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_packet_stream_short_internal_flow_same_subnet(self):
        self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_SHORT,
                                           vm1_net=self.main_network,
                                           vm1_subnet=self.main_subnet,
                                           vm2_net=self.main_network,
                                           vm2_subnet=self.main_subnet)

    def test_packet_stream_med_internal_flow_same_subnet(self):
        self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_MEDIUM,
                                           vm1_net=self.main_network,
                                           vm1_subnet=self.main_subnet,
                                           vm2_net=self.main_network,
                                           vm2_subnet=self.main_subnet)

    def test_packet_stream_long_internal_flow_same_subnet(self):
        self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_LONG,
                                           vm1_net=self.main_network,
                                           vm1_subnet=self.main_subnet,
                                           vm2_net=self.main_network,
                                           vm2_subnet=self.main_subnet)

    def test_packet_stream_short_internal_flow_separate_subnet(self):
        new_net = None
        new_subnet = None
        try:
            new_net = self.api.create_network({'network': {'name': 'new_net',
                                                           'tenant_id': 'admin'}})['network']
            new_subnet = self.api.create_subnet({'subnet': {'name': 'new_sub',
                                                            'network_id': new_net['id'],
                                                            'ip_version': 4, 'cidr': '192.168.23.0/24',
                                                            'tenant_id': 'admin'}})['subnet']
            self.LOG.debug('Created subnet: ' + str(new_subnet))
            self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_SHORT,
                                               vm1_net=self.main_network,
                                               vm1_subnet=self.main_subnet,
                                               vm2_net=new_net,
                                               vm2_subnet=new_subnet)
        finally:
            if new_subnet:
                self.api.delete_subnet(new_subnet['id'])
                self.LOG.debug('Deleted subnet: ' + new_subnet['id'])
            if new_net:
                self.api.delete_network(new_net['id'])
                self.LOG.debug('Deleted network: ' + new_net['id'])

    def test_packet_stream_med_internal_flow_separate_subnet(self):
        new_net = None
        new_subnet = None
        try:
            new_net = self.api.create_network({'network': {'name': 'new_net',
                                                           'tenant_id': 'admin'}})['network']
            new_subnet = self.api.create_subnet({'subnet': {'name': 'new_sub',
                                                            'network_id': new_net['id'],
                                                            'ip_version': 4, 'cidr': '192.168.23.0/24',
                                                            'tenant_id': 'admin'}})['subnet']
            self.LOG.debug('Created subnet: ' + str(new_subnet))
            self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_MED,
                                               vm1_net=self.main_network,
                                               vm1_subnet=self.main_subnet,
                                               vm2_net=new_net,
                                               vm2_subnet=new_subnet)
        finally:
            if new_subnet:
                self.api.delete_subnet(new_subnet['id'])
                self.LOG.debug('Deleted subnet: ' + new_subnet['id'])
            if new_net:
                self.api.delete_network(new_net['id'])
                self.LOG.debug('Deleted network: ' + new_net['id'])

    def test_packet_stream_long_internal_flow_separate_subnet(self):
        new_net = None
        new_subnet = None
        try:
            new_net = self.api.create_network({'network': {'name': 'new_net',
                                                           'tenant_id': 'admin'}})['network']
            new_subnet = self.api.create_subnet({'subnet': {'name': 'new_sub',
                                                            'network_id': new_net['id'],
                                                            'ip_version': 4, 'cidr': '192.168.23.0/24',
                                                            'tenant_id': 'admin'}})['subnet']
            self.LOG.debug('Created subnet: ' + str(new_subnet))
            self.create_vms_and_stream_packets(num_packets=PACKETS_TO_SEND_LONG,
                                               vm1_net=self.main_network,
                                               vm1_subnet=self.main_subnet,
                                               vm2_net=new_net,
                                               vm2_subnet=new_subnet)
        finally:
            if new_subnet:
                self.api.delete_subnet(new_subnet['id'])
                self.LOG.debug('Deleted subnet: ' + new_subnet['id'])
            if new_net:
                self.api.delete_network(new_net['id'])
                self.LOG.debug('Deleted network: ' + new_net['id'])
