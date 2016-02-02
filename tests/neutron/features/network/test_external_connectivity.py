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

from TSM.NeutronTestCase import NeutronTestCase, require_extension
from collections import namedtuple
from common.Exceptions import *
from common.IP import IP
import CBT.VersionConfig as version_config
import unittest


class TestExternalConnectivity(NeutronTestCase):
    @require_extension('extraroute')
    def test_neutron_api_ping_external(self):
        port1 = None
        vm1 = None
        edge_data = None

        try:
            edge_data = self.create_edge_router()

            port1def = {'port': {'name': 'port1',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']
            self.LOG.info('Created port 1: ' + str(port1))

            self.LOG.info("Got VM1 IP: " + str(ip1))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'])

            vm1.plugin_vm('eth0', port1['id'])

            ext_host = self.ptm.impl_.hosts_by_name['ext1']
            """:type: Host"""
            ext_ip = ext_host.interfaces['eth0'].ip_list[0].ip

            # Test Ping
            self.LOG.info('Pinging from VM1 to external')
            self.assertTrue(vm1.ping(target_ip=ext_ip))

            # Test TCP
            ext_host.start_echo_server(ip=ext_ip)
            echo_response = vm1.send_echo_request(dest_ip=ext_ip)
            self.assertEqual('ping:echo-reply', echo_response)
            ext_host.stop_echo_server(ip=ext_ip)

            # Test UDP
            # TODO: Fix UDP
            # ext_host.start_echo_server(ip=ext_ip, protocol='udp')
            # echo_response = vm1.send_echo_request(dest_ip=ext_ip, protocol='udp')
            # self.assertEqual('ping:echo-reply', echo_response)

        finally:
            if vm1 is not None:
                vm1.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])

            self.delete_edge_router(edge_data)

