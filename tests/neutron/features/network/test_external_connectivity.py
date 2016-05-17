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

import time
from zephyr.common import ip
from zephyr.common import pcap
from zephyr.tsm import neutron_test_case


class TestExternalConnectivity(neutron_test_case.NeutronTestCase):
    @neutron_test_case.require_extension('extraroute')
    def test_neutron_api_ping_external(self):
        self.create_edge_router()

        (port1, vm1, ip1) = self.create_vm_server(
            "vm1",
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])

        ext_host = self.ptm.impl_.hosts_by_name['ext1']
        """:type: zephyr.ptm.host.host.Host"""
        ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        # Test Ping
        self.LOG.info('Pinging from VM1 to external')
        self.assertTrue(vm1.ping(target_ip=ext_ip))

        # Test TCP
        ext_host.start_echo_server(ip=ext_ip)
        echo_response = vm1.send_echo_request(dest_ip=ext_ip)
        self.assertEqual('ping:echo-reply', echo_response)
        ext_host.stop_echo_server(ip=ext_ip)

        # Test UDP
        # TODO(micucci): Fix UDP
        # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
        # echo_response = vm1.send_echo_request(
        #   ddddsdfdest_ip=ext_ip, protocol='udp')
        # self.assertEqual('ping:echo-reply', echo_response)


    @neutron_test_case.require_extension('extraroute')
    def test_neutron_delete_readd_ext_router(self):
        edge_data = self.create_edge_router()

        (port1, vm1, ip1) = self.create_vm_server(
            "vm1",
            net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'])

        ext_host = self.ptm.impl_.hosts_by_name['ext1']
        """:type: Host"""
        ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))

        # Test Ping
        self.LOG.info('Pinging from VM1 to external')
        self.assertTrue(vm1.ping(target_ip=ext_ip))

        # Test TCP
        ext_host.start_echo_server(ip=ext_ip)
        echo_response = vm1.send_echo_request(dest_ip=ext_ip)
        self.assertEqual('ping:echo-reply', echo_response)
        ext_host.stop_echo_server(ip=ext_ip)

        # Delete and re-add exterior router
        self.delete_edge_router(edge_data)

        edge_data = self.create_edge_router()

        # Test Ping
        self.LOG.info('Pinging again from VM1 to external')
        self.assertTrue(vm1.ping(target_ip=ext_ip))

        # Test TCP
        ext_host.start_echo_server(ip=ext_ip)
        echo_response = vm1.send_echo_request(dest_ip=ext_ip)
        self.assertEqual('ping:echo-reply', echo_response)

    @require_extension('extraroute')
    def test_neutron_api_ping_with_high_id(self):
        self.create_edge_router(edge_host_name='edge1',
                                edge_subnet_cidr='172.16.2.0/24')
        self.create_edge_router(edge_host_name='edge2',
                                edge_subnet_cidr='172.17.2.0/24',
                                gateway=False)

        (porta, vm1, ipa) = self.create_vm_server(
            "pinger", self.main_network['id'],
            self.main_subnet['gateway_ip'])
        """:type: (str, zephyr.vtm.guest.Guest, str)"""

        ext_host = self.ptm.impl_.hosts_by_name['ext1']
        """:type: Host"""
        ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip
        ext_host.add_route(
            route_ip=ip.IP.make_ip(self.pub_subnet['cidr']),
            gw_ip=ip.IP('.'.join(ext_ip.split('.')[:3]) + '.2'))
        vm1.start_capture('eth0', pfilter=pcap.ICMPProto())

        # Test Ping
        self.LOG.info('Pinging from VM1 to external')
        self.assertTrue(vm1.ping(target_ip=ext_ip))

        ret0 = vm1.capture_packets('eth0', count=2, timeout=15)
        self.assertEqual(2, len(ret0))

        # Test Ping with set ID
        self.LOG.info('Pinging from VM1 to external with '
                      'low ICMP ID')
        vm1.send_packet(on_iface='eth0', dest_ip=ext_ip,
                        packet_type='icmp',
                        packet_options={'command': 'ping', 'id': '3'})

        ret1 = vm1.capture_packets('eth0', count=2, timeout=15)
        self.assertEqual(2, len(ret1))

        self.LOG.info('Pinging from VM1 to external with '
                      'high ICMP ID')
        vm1.send_packet(on_iface='eth0', dest_ip=ext_ip,
                        packet_type='icmp',
                        packet_options={'command': 'ping', 'id': '35000'})

        ret2 = vm1.capture_packets('eth0', count=2, timeout=5)
        self.assertEqual(2, len(ret2))

        vm1.stop_capture('eth0')
