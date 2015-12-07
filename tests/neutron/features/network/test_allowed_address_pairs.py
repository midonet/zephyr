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

from common.PCAPRules import *
from common.PCAPPacket import *
from TSM.NeutronTestCase import NeutronTestCase
from tests.scenarios.Scenario_Basic2Compute import Scenario_Basic2Compute
from VTM.Guest import Guest

from collections import namedtuple
from neutronclient.common.exceptions import *

import unittest

class TestAllowedAddressPairs(NeutronTestCase):
    @staticmethod
    def supported_scenarios():
        return {Scenario_Basic2Compute}

    def send_and_capture_spoof(self, sender, receiver, receiver_ip, spoof_ip, spoof_mac,
                               with_ip=True, with_mac=True, should_fail=False):
        """
        :param sender: VMHost
        :param receiver: VMHost
        :param receiver_ip: str
        :return:
        """

        pcap_filter_list = [PCAP_ICMPProto()]
        if with_ip:
            pcap_filter_list.append(PCAP_Host(spoof_ip, proto='ip', source=True, dest=False))
        if with_mac:
            pcap_filter_list.append(PCAP_Host(spoof_mac, proto='ether', source=True, dest=False))
        receiver.start_capture(on_iface='eth0', count=1,
                               filter=PCAP_And(pcap_filter_list))

        send_args = {'dest_ip': receiver_ip}
        if with_ip:
            send_args['source_ip'] = spoof_ip
        if with_mac:
            send_args['source_mac'] = spoof_mac

        sender.send_packet(on_iface='eth0',
                           packet_type='icmp', packet_options={'command': 'ping'},
                           **send_args)
        packets = []
        try:
            packets = receiver.capture_packets(on_iface='eth0', count=1, timeout=3)
            if should_fail:
                self.fail('Spoofed packet to IP: ' + spoof_ip + " and MAC: " + spoof_mac +
                          'should not have been received!')
            self.assertEqual(1, len(packets))
        except SubprocessTimeoutException as e:
            if not should_fail:
                import traceback
                import sys
                self.LOG.error(traceback.format_tb(sys.exc_traceback))
                self.fail("Sending spoofed packet with IP: " + spoof_ip + " and MAC: " + spoof_mac +
                          " to destination: " + receiver_ip + " failed: " + str(e))
            else:
                self.assertEqual(0, len(packets))
        finally:
            receiver.stop_capture(on_iface='eth0')

    def test_allowed_address_pairs_normal_antispoof(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Default state should be PS enabled on net and any created ports
            # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_single_ip(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.99"}
                                                   ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="",
                                        with_mac=False)
            """ :type: list[PCAPPacket]"""

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_single_ip_mac(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.99/32",
                                                        "mac_address": "AA:AA:AA:AA:AA:AA"}
                                                   ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to spoof IP with spoof MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA")

            # Send to spoof IP with default MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="", with_mac=False,
                                        should_fail=True)

            # Send to default IP with spoof MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="", with_ip=False, spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_multi_ip_and_mac(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.99",
                                                        "mac_address": "AA:AA:AA:AA:AA:AA"},
                                                       {"ip_address": "192.168.99.98",
                                                        "mac_address": "AA:AA:AA:AA:AA:BB"},
                                                       {"ip_address": "192.168.99.97",
                                                        "mac_address": "AA:AA:AA:AA:AA:CC"}
                                                   ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to ip1 and mac1
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA")

            # Send to ip2 and mac2
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:BB")

            # Send to ip3 and mac3
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.97", spoof_mac="AA:AA:AA:AA:AA:CC")

            # Send to ip1 and mac3 - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:CC",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_ip_double_mac(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            # Duplicate IP with different MACs
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.99",
                                                        "mac_address": "AA:AA:AA:AA:AA:AA"},
                                                       {"ip_address": "192.168.99.99",
                                                        "mac_address": "AA:AA:AA:AA:AA:DD"}
                                                   ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA")

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:DD")

            #Send to default IP and mac2 - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="", with_ip=False, spoof_mac="AA:AA:AA:AA:AA:DD",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_ip_subnet(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.0/24"},
                                                       ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.2", spoof_mac="", with_mac=False)

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.250", spoof_mac="", with_mac=False)

            # Send to subnet spoof IP, different MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)

            # Send to default IP, different MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="", with_ip=False, spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)
        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_ip_mac_subnet(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.0/24",
                                                        "mac_address": "AA:AA:AA:AA:AA:AA"}
                                                       ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.2", spoof_mac="AA:AA:AA:AA:AA:AA")

            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.250", spoof_mac="AA:AA:AA:AA:AA:AA")

            # Send to default IP with mac1 - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="", with_ip=False, spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_updates(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.0/24"}
                                                   ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            # Default IP and MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to subnet spoof IP with default MAC, should work
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.2", spoof_mac="", with_mac=False)

            # Now update allowed pair list to ADD a new IP and make sure that works
            port1 = self.api.update_port(port1['id'], {'port':
                                                           {'allowed_address_pairs': [
                                                               {"ip_address": "192.168.99.0/24"},
                                                               {"ip_address": "192.168.98.96",
                                                                "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Send to new IP and new MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.96", spoof_mac="AA:AA:AA:AA:AA:DD")

            # Still can spoof to old IPs
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="", with_mac=False)

            # Send to old subnet IP with new MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.96", spoof_mac="AA:AA:AA:AA:AA:DD",
                                        should_fail=True)

            # Now update allowed address pairs to CHANGE to a straight-IP format (not subnet)
            port1 = self.api.update_port(port1['id'], {'port':
                                                           {'allowed_address_pairs': [
                                                               {"ip_address": "192.168.99.99",
                                                                "mac_address": "AA:AA:AA:AA:AA:AA"},
                                                               {"ip_address": "192.168.99.98",
                                                                "mac_address": "AA:AA:AA:AA:AA:BB"},
                                                               {"ip_address": "192.168.98.96",
                                                                "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Send to old specific IP with old mac
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.96", spoof_mac="AA:AA:AA:AA:AA:DD")

            # Send to new specific IP2 and mac2
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:BB")

            # Send to new specific IP2 and default mac - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="", with_mac=False,
                                        should_fail=True)

            # Send to old subnet spoof IP (now deleted) and default mac - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.2", spoof_mac="", with_mac=False,
                                        should_fail=True)

            # Now update allowed address pairs to CHANGE one of the IP's mac addresses
            port1 = self.api.update_port(port1['id'], {'port':
                                                           {'allowed_address_pairs': [
                                                               {"ip_address": "192.168.99.99",
                                                                "mac_address": "AA:AA:AA:AA:AA:AA"},
                                                               {"ip_address": "192.168.99.98",
                                                                "mac_address": "AA:AA:AA:AA:AA:99"},
                                                               {"ip_address": "192.168.98.96",
                                                                "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Send to IP2 and new mac2
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:99")

            # Send to IP2 and old mac2 - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:BB",
                                        should_fail=True)

            # Next update the allowed address pairs to REMOVE an entry
            port1 = self.api.update_port(port1['id'], {'port':
                                                           {'allowed_address_pairs': [
                                                               {"ip_address": "192.168.99.99",
                                                                "mac_address": "AA:AA:AA:AA:AA:AA"},
                                                               {"ip_address": "192.168.98.96",
                                                                "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Send to IP2 and mac2
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.96", spoof_mac="AA:AA:AA:AA:AA:DD")

            # Send to IP1 and mac1
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA")

            # Send to deleted IP/mac - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.98", spoof_mac="AA:AA:AA:AA:AA:BB",
                                        should_fail=True)

            # Last, CLEAR all entries
            port1 = self.api.update_port(port1['id'], {'port':
                                                           {'allowed_address_pairs': []}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Default IP/MAC should still work
            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to deleted IP/mac - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_ip_subnet_with_specific_ip(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            # Create IP subnet and IP within subnet
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.0/24"},
                                                       {"ip_address": "192.168.99.98"},
                                                       ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to subnet IP with default MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.2", spoof_mac="", with_mac=False)

            # Send to specific IP with default MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="", with_mac=False)

            # Now update allowed pair list to ADD a new IP/MAC and make sure that works
            port1 = self.api.update_port(port1['id'],
                                         {'port': {'allowed_address_pairs': [
                                             {"ip_address": "192.168.99.0/24"},
                                             {"ip_address": "192.168.99.98"},
                                             {"ip_address": "192.168.99.97",
                                              "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
            self.LOG.debug('Updated port1: ' + str(port1))

            # Send to new specific IP with new MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.97", spoof_mac="AA:AA:AA:AA:AA:DD")

            # Send to specific IP with default MAC (as a part of the subnet definition)
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.97", spoof_mac="", with_mac=False)

            # Still can spoof to old IPs
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="", with_mac=False)

            # Send to old IP with new MAC - should FAIL
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:DD",
                                        should_fail=True)

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_ip_subnet_with_mixed_ips_macs(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            # Create IP subnet and IP within subnet
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'allowed_address_pairs': [
                                                       {"ip_address": "192.168.99.0/24"},
                                                       {"ip_address": "192.168.99.98",
                                                        "mac_address": "AA:AA:AA:AA:AA:DD"},
                                                       {"ip_address": "192.168.98.0/24",
                                                        "mac_address": "AA:AA:AA:AA:AA:CC"},
                                                       {"ip_address": "192.168.98.5"},
                                                       ],
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port2: ' + str(port2))

            ip1 = port1['fixed_ips'][0]['ip_address']
            ip2 = port2['fixed_ips'][0]['ip_address']

            vm1 = self.vtm.create_vm(ip=ip1, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip=ip2, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'], port1['mac_address'])
            vm2.plugin_vm('eth0', port2['id'], port2['mac_address'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

            # Send to subnet, default MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.66", spoof_mac="", with_mac=False)

            # Send to subnet, spoof MAC - should fail
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.66", spoof_mac="AA:AA:AA:AA:AA:DD",
                                        should_fail=True)

            # Send to specific IP, spoofed MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="AA:AA:AA:AA:AA:DD")

            # Send to specific IP as part of subnet, default MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.99.98", spoof_mac="", with_mac=False)

            # Send to subnet, spoofed MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.77", spoof_mac="AA:AA:AA:AA:AA:CC")

            # Send to subnet IP, default MAC - should fail
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.77", spoof_mac="", with_mac=False,
                                        should_fail=True)

            # Send to specific IP, default MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.5", spoof_mac="", with_mac=False)

            # Send to specific IP as part of subnet, spoofed MAC
            self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                        spoof_ip="192.168.98.5", spoof_mac="AA:AA:AA:AA:AA:CC")

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_allowed_address_pairs_error(self):
        # Allowed address pair must have IP address
        try:
            p = self.api.create_port({'port': {'name': 'port1',
                                               'network_id': self.main_network['id'],
                                               'admin_state_up': True,
                                               'allowed_address_pairs': [
                                                   {"mac_address": "AA:AA:AA:AA:AA:AA"}
                                               ],
                                               'tenant_id': 'admin'}})['port']
            self.fail("Should have thrown BadRequest when IP Address is missing.")
        except BadRequest:
            pass
        except:
            self.fail("Should have thrown BadRequest when IP Address is missing.")
