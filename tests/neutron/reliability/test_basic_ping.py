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


class TestBasicPing(NeutronTestCase):

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
            self.LOG.info('Created port 1: ' + str(port1))

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.LOG.info('Created port 2: ' + str(port2))

            self.LOG.info("Got VM1 IP: " + str(ip1))
            self.LOG.info("Got VM2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], hv_host='cmp2')
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], hv_host='cmp2')

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            self.LOG.info('Pinging from VM1 to VM2')
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            self.LOG.info('Pinging from VM2 to VM1')
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
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            self.LOG.info('Created port 1: ' + str(port1))

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.LOG.info('Created port 2: ' + str(port2))

            self.LOG.info("Got VM1 IP: " + str(ip1))
            self.LOG.info("Got VM2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(ip1, mac=port1['mac_address'], hv_host='cmp1', name='vm1')
            vm2 = self.vtm.create_vm(ip2, mac=port2['mac_address'], hv_host='cmp2', name='vm2')

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            self.LOG.info('Pinging from VM1 to VM2')
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
