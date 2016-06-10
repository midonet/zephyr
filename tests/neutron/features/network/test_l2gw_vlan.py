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

from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.vtm.l2gw_fixture import L2GWFixture


class TestL2GWVLAN(NeutronTestCase):
    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(TestL2GWVLAN, cls)._prepare_class(ptm, vtm,
                                                test_case_logger)

        # Add the l2gw fixture if it's not already added
        if 'l2gw-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding l2gw-setup fixture')
            ptm.add_fixture('l2gw-setup', L2GWFixture())

    @require_extension('extraroute')
    @require_extension('gateway-device')
    @require_extension('l2-gateway')
    def test_vlan_traffic_stays_on_vlan(self):
        # Create the VLAN-aware bridge (will get set as l2gw device later)
        vlan_aware_net = self.create_network(
            "vlan_net", port_security_enabled=False)
        vlan_aware_sub = self.create_subnet(
            "vlan_sub", vlan_aware_net['id'], '10.0.250.0/24')

        # Create the normal tenant networks
        tenant1_net = self.create_network("net1_net")
        tenant1_sub = self.create_subnet(
            "net1_sub", tenant1_net['id'], '172.20.100.0/24')

        tenant2_net = self.create_network("net2_net")
        tenant2_sub = self.create_subnet(
            "net2_sub", tenant2_net['id'], '172.20.100.0/24')

        # Turn the VLAN-aware bridge into a l2gw device
        gw_dev = self.create_gateway_device(
            resource_id=vlan_aware_net['id'],
            dev_type='network_vlan')

        # Create the L2 connections to the tenant networks
        l2_100 = self.create_l2_gateway(
            name='VLAN_100', gwdev_id=gw_dev['id'])
        l2_conn_100 = self.create_l2_gateway_connection(
            net_id=tenant1_net['id'],
            segment_id='100',
            l2gw_id=l2_100['id'])

        l2_200 = self.create_l2_gateway(
            name='VLAN_200', gwdev_id=gw_dev['id'])
        l2_conn_200 = self.create_l2_gateway_connection(
            net_id=tenant2_net['id'],
            segment_id='200',
            l2gw_id=l2_200['id'])

        # Trunk Port for VLAN-aware bridge
        vlan_trunk_port = self.create_port(
            "vlan_trunk", vlan_aware_net['id'], ip="10.0.250.240",
            host='cmp1', host_iface='eth1', port_security_enabled=False)

        # VLAN 100 VM
        (port1, vm1, ip1) = self.create_vm_server(
            "vm1", tenant1_net['id'], tenant1_sub['gateway_ip'])

        # VLAN 200 VM
        (port2, vm2, ip2) = self.create_vm_server(
            "vm2", tenant2_net['id'], tenant2_sub['gateway_ip'])

        ext2_host = self.ptm.impl_.hosts_by_name['ext2']
        ext3_host = self.ptm.impl_.hosts_by_name['ext3']

        ext_ip = "172.20.100.224"

        vm1.start_echo_server(ip=ip1, port=5080, echo_data="vm1")
        vm2.start_echo_server(ip=ip2, port=5081, echo_data="vm2")
        ext2_host.start_echo_server(ip=ext_ip, port=5082, echo_data="ext2")
        ext3_host.start_echo_server(ip=ext_ip, port=5083, echo_data="ext3")

        try:
            # From VMs in VLAN to ext host in VLAN should work
            self.assertEqual(
                "vm1:ext2",
                vm1.send_echo_request(
                    dest_ip=ext_ip, dest_port=5082, echo_request='vm1'))
            self.assertEqual(
                "vm2:ext3",
                vm2.send_echo_request(
                    dest_ip=ext_ip, dest_port=5083, echo_request='vm2'))

            # From ext hosts in VLAN to VM in VLAN should work
            self.assertEqual(
                "ext2:vm1",
                ext2_host.send_echo_request(
                    dest_ip=ip1, dest_port=5080, echo_request='ext2'))
            self.assertEqual(
                "ext3:vm2",
                ext3_host.send_echo_request(
                    dest_ip=ip2, dest_port=5081, echo_request='ext3'))

            # From VMs to ext hosts in different VLAN should NOT work
            self.assertEqual(
                "",
                vm2.send_echo_request(
                    dest_ip=ext_ip, dest_port=5082, echo_request='vm2'))
            self.assertEqual(
                "",
                vm1.send_echo_request(
                    dest_ip=ext_ip, dest_port=5083, echo_request='vm1'))
        finally:
            ext2_host.stop_echo_server(ip=ext_ip, port=5082)
            ext3_host.stop_echo_server(ip=ext_ip, port=5083)
            vm1.stop_echo_server(ip=ip1, port=5080)
            vm2.stop_echo_server(ip=ip2, port=5081)
