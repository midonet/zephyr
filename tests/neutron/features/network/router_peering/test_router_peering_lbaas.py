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

from common.Utils import curl_post, curl_delete

from TSM.NeutronTestCase import require_extension
from TSM.TestCase import expected_failure, require_topology_feature
from VTM.NeutronAPI import *
from VTM.Guest import Guest

from router_peering_utils import L2GWNeutronTestCase, L2GWSiteData

import operator


class TestRouterPeeringLBaaS(L2GWNeutronTestCase):
    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    @require_topology_feature('config_file', lambda a, b: a in b,
                              ['config/physical_topologies/2z-3c-2edge.json'])
    def test_peered_rotuers_with_lbaas(self):
        vm1 = None
        vm2 = None
        ip1 = None
        ip2 = None
        port1 = None
        port2 = None

        east_topo = None
        east_l2gw_topo = None
        west_topo = None
        west_l2gw_topo = None

        peered_topo = None

        segment_id = '100'

        east_main_cidr = "192.168.20.0/24"
        west_main_cidr = "192.168.30.0/24"

        try:

            east_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_east',
                    main_subnet_cidr=east_main_cidr,
                    pub_name='pub_east',
                    pub_subnet_cidr="200.200.120.0/24",
                    log=self.LOG)
            west_topo = create_neutron_main_pub_networks(
                    self.api,
                    main_name='main_west',
                    main_subnet_cidr=west_main_cidr,
                    pub_name='pub_west',
                    pub_subnet_cidr="200.200.130.0/24",
                    log=self.LOG)

            port1 = self.api.create_port({
                'port': {'name': 'port_vm1',
                         'network_id': east_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(
                    ip=ip1,
                    mac=port1['mac_address'],
                    gw_ip=east_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])

            port2 = self.api.create_port({
                'port': {'name': 'port_vm2',
                         'network_id': west_topo.main_net.network['id'],
                         'admin_state_up': True,
                         'tenant_id': 'admin'}})['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm2 = self.vtm.create_vm(
                    ip=ip2,
                    mac=port2['mac_address'],
                    gw_ip=west_topo.main_net.subnet['gateway_ip'])
            """ :type: Guest"""

            vm2.plugin_vm('eth0', port2['id'])

            # Test that VM canNOT reach via internal IP
            # Ping
            self.assertFalse(vm1.ping(target_ip=ip2))
            self.assertFalse(vm2.ping(target_ip=ip1))

            # Peer the routers!
            east_l2gw_topo = self.setup_peer_l2gw("1.1.1.0/24", "1.1.1.2",
                                                  "1.1.1.3", "tun2", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.2", segment_id,
                                                  east_topo.router.router,
                                                  "EAST")
            west_l2gw_topo = self.setup_peer_l2gw("2.2.2.0/24", "2.2.2.2",
                                                  "2.2.2.3", "tun1", "eth1",
                                                  "192.168.200.0/24",
                                                  "192.168.200.3", segment_id,
                                                  west_topo.router.router,
                                                  "WEST")

            peered_topo = self.peer_sites(east=east_l2gw_topo,
                                          east_private_cidr=east_main_cidr,
                                          west=west_l2gw_topo,
                                          west_private_cidr=west_main_cidr,
                                          segment_id=segment_id)

            # Test that VM1 can reach VM2 via internal IP
            # Ping
            self.assertTrue(vm1.ping(target_ip=ip2))
            self.assertTrue(vm2.ping(target_ip=ip1))

            # TCP
            vm2.start_echo_server(ip=ip2)
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm1.send_echo_request(dest_ip=ip2)
            self.assertEqual('ping:echo-reply', echo_response)

            # TCP
            vm1.start_echo_server(ip=ip1)
            echo_response = vm2.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

            # Send second packet
            echo_response = vm2.send_echo_request(dest_ip=ip1)
            self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if vm2 and ip2:
                vm2.stop_echo_server(ip=ip2)

            if vm1 and ip1:
                vm1.stop_echo_server(ip=ip1)

            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.clean_peered_site(peered_topo)
            self.clean_peer(east_l2gw_topo)
            self.clean_peer(west_l2gw_topo)

            delete_neutron_main_pub_networks(self.api, east_topo)
            delete_neutron_main_pub_networks(self.api, west_topo)
