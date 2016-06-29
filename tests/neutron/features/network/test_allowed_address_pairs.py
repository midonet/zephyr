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

from neutronclient.common.exceptions import BadRequest
from zephyr.common.exceptions import *
from zephyr.common import pcap
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension


class TestAllowedAddressPairs(NeutronTestCase):
    def send_and_capture_spoof(
            self, sender, receiver, receiver_ip, spoof_ip, spoof_mac,
            with_ip=True, with_mac=True, should_fail=False):
        """
        :type sender: zephyr.vtm.guest.Guest
        :type receiver: zephyr.vtm.guest.Guest
        :type receiver_ip: str
        :return:
        """

        pcap_filter_list = [pcap.ICMPProto()]
        """ :type: list[zephyr.common.pcap.Rule]"""
        if with_ip:
            pcap_filter_list.append(pcap.Host(spoof_ip, proto='ip',
                                              source=True, dest=False))
        if with_mac:
            pcap_filter_list.append(pcap.Host(spoof_mac, proto='ether',
                                              source=True, dest=False))
        receiver.start_capture(on_iface='eth0', count=1,
                               pfilter=pcap.And(pcap_filter_list))

        send_args = {'dest_ip': receiver_ip}
        if with_ip:
            send_args['source_ip'] = spoof_ip
        if with_mac:
            send_args['source_mac'] = spoof_mac

        sender.send_packet(on_iface='eth0',
                           packet_type='icmp',
                           packet_options={'command': 'ping'},
                           **send_args)
        packets = []
        try:
            packets = receiver.capture_packets(on_iface='eth0',
                                               count=1, timeout=3)
            if should_fail:
                self.fail('Spoofed packet to IP: ' + spoof_ip +
                          " and MAC: " + spoof_mac +
                          'should not have been received!')
            self.assertEqual(1, len(packets))
        except SubprocessTimeoutException as e:
            if not should_fail:
                import sys
                import traceback
                self.LOG.error(traceback.format_tb(sys.exc_traceback))
                self.fail("Sending spoofed packet with IP: " + spoof_ip +
                          " and MAC: " + spoof_mac +
                          " to destination: " + receiver_ip + " failed: " +
                          str(e))
            else:
                self.assertEqual(0, len(packets))
        finally:
            receiver.stop_capture(on_iface='eth0')

    def test_allowed_address_pairs_normal_antispoof(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Default state should be PS enabled on net and any created ports
        # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
        self.send_and_capture_spoof(
            sender=vm1, receiver=vm2, receiver_ip=ip2,
            spoof_ip="192.168.99.99", spoof_mac="AA:AA:AA:AA:AA:AA",
            should_fail=True)

    def test_allowed_address_pairs_reply_antispoof_same_network(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))
        new_ip = '.'.join(ip2.split('.')[0:3]) + '.155'
        vm2.execute('ip a add ' + new_ip + '/24 dev eth0')

        vm2.start_echo_server(ip_addr=new_ip)

        # Echo request should work, but reply will be blocked
        echo_data = vm1.send_echo_request(dest_ip=new_ip)
        self.assertEqual('', echo_data)

        # Ping to spoofed IP should work, but reply should be blocked
        self.assertFalse(vm1.ping(target_ip=new_ip, on_iface='eth0',
                                  timeout=5))

    def test_allowed_address_pairs_reply_antispoof_diff_network(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        # Create a first network for testing
        net1 = self.create_network(name='net1')
        subnet1 = self.create_subnet(name='net1_sub', net_id=net1['id'],
                                     cidr='10.0.50.0/24')

        # Create a second network for testing
        net2 = self.create_network(name='net2')
        subnet2 = self.create_subnet(name='net2_sub', net_id=net2['id'],
                                     cidr='10.0.55.0/24')

        self.create_router(
            name='router1to2',
            priv_sub_ids=[subnet1['id'], subnet2['id']])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=net1['id'],
            gw_ip=subnet1['gateway_ip'],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=net2['id'],
            gw_ip=subnet2['gateway_ip'],
            sgs=[aap_sg['id']])

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        new_ip = '.'.join(ip2.split('.')[0:3]) + '.155'
        vm2.execute('ip a add ' + new_ip + '/24 dev eth0')

        vm2.start_echo_server(ip_addr=new_ip)

        # Echo request should work, but reply will be blocked
        echo_data = vm1.send_echo_request(dest_ip=new_ip)
        self.assertEqual('', echo_data)

        # Ping to spoofed IP should work, but reply should be blocked
        self.assertFalse(vm1.ping(target_ip=new_ip, on_iface='eth0',
                                  timeout=5))

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_single_ip(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.99",)],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99", spoof_mac="",
                                    with_mac=False)
        """ :type: list[PCAPPacket]"""

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_single_ip_round_trip(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))
        new_ip = '.'.join(ip2.split('.')[0:3]) + '.235'
        vm2.execute('ip a add ' + new_ip + '/24 dev eth0')

        vm2.start_echo_server(ip_addr=new_ip)

        # Echo request should work, but reply will be blocked
        echo_data = vm1.send_echo_request(dest_ip=new_ip)
        self.assertEqual('', echo_data)

        # Ping to spoofed IP should work, but reply should be blocked
        self.assertFalse(vm1.ping(target_ip=new_ip, on_iface='eth0',
                                  timeout=5))

        # Update with AAP
        port2 = self.api.update_port(port2['id'],
                                     {'port': {'allowed_address_pairs': [
                                         {"ip_address": new_ip}]}})['port']
        self.LOG.debug('Updated port2: ' + str(port2))

        # Echo request should work now
        echo_data = vm1.send_echo_request(dest_ip=new_ip)
        self.assertEqual('ping:echo-reply', echo_data)

        # Ping to spoofed IP should work now
        self.assertTrue(vm1.ping(target_ip=new_ip, on_iface='eth0',
                                 timeout=30))

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_single_ip_mac(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.99/32", "AA:AA:AA:AA:AA:AA")],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to spoof IP with spoof MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        # Send to spoof IP with default MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99", spoof_mac="",
                                    with_mac=False,
                                    should_fail=True)

        # Send to default IP with spoof MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="", with_ip=False,
                                    spoof_mac="AA:AA:AA:AA:AA:AA",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_multi_ip_and_mac(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.99", "AA:AA:AA:AA:AA:AA"),
                                   ("192.168.99.98", "AA:AA:AA:AA:AA:BB"),
                                   ("192.168.99.97", "AA:AA:AA:AA:AA:CC")],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.98/32')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.97/32')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to ip1 and mac1
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        # Send to ip2 and mac2
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:BB")

        # Send to ip3 and mac3
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.97",
                                    spoof_mac="AA:AA:AA:AA:AA:CC")

        # Send to ip1 and mac3 - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:CC",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_ip_double_mac(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.99", "AA:AA:AA:AA:AA:AA"),
                                   ("192.168.99.99", "AA:AA:AA:AA:AA:DD")],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Send to default IP and mac2 - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="", with_ip=False,
                                    spoof_mac="AA:AA:AA:AA:AA:DD",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_ip_subnet(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.0/24",)],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.0/24')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.2",
                                    spoof_mac="", with_mac=False)

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.250",
                                    spoof_mac="", with_mac=False)

        # Send to subnet spoof IP, different MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:AA",
                                    should_fail=True)

        # Send to default IP, different MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="", with_ip=False,
                                    spoof_mac="AA:AA:AA:AA:AA:AA",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_ip_mac_subnet(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.0/24", "AA:AA:AA:AA:AA:AA")],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.0/24')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.2",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.250",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        # Send to default IP with mac1 - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="", with_ip=False,
                                    spoof_mac="AA:AA:AA:AA:AA:AA",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_updates(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.0/24",)],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        sgr99_0 = self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.0/24')

        # Default IP and MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to subnet spoof IP with default MAC, should work
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.2",
                                    spoof_mac="", with_mac=False)

        # Now update allowed pair list to ADD a new IP and make
        # sure that works
        port1 = self.api.update_port(port1['id'], {'port': {
            'allowed_address_pairs': [
                {"ip_address": "192.168.99.0/24"},
                {"ip_address": "192.168.98.96",
                 "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        sgr98_96 = self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.98.96/32')

        # Send to new IP and new MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.96",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Still can spoof to old IPs
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="", with_mac=False)

        # Send to old subnet IP with new MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.96",
                                    spoof_mac="AA:AA:AA:AA:AA:DD",
                                    should_fail=True)

        # Now update allowed address pairs to CHANGE to a
        # straight-IP format (not subnet)
        port1 = self.api.update_port(port1['id'], {'port': {
            'allowed_address_pairs': [
                {"ip_address": "192.168.99.99",
                 "mac_address": "AA:AA:AA:AA:AA:AA"},
                {"ip_address": "192.168.99.98",
                 "mac_address": "AA:AA:AA:AA:AA:BB"},
                {"ip_address": "192.168.98.96",
                 "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        self.delete_security_group_rule(sgr99_0['id'])

        sgr99_99 = self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.99/32')
        sgr99_98 = self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.98/32')

        # Send to old specific IP with old mac
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.96",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Send to new specific IP2 and mac2
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:BB")

        # Send to new specific IP2 and default mac - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="", with_mac=False,
                                    should_fail=True)

        # Send to old subnet spoof IP (now deleted) and default
        # mac - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.2",
                                    spoof_mac="", with_mac=False,
                                    should_fail=True)

        # Now update allowed address pairs to CHANGE one of the
        # IP's mac addresses
        port1 = self.api.update_port(port1['id'], {'port': {
            'allowed_address_pairs': [
                {"ip_address": "192.168.99.99",
                 "mac_address": "AA:AA:AA:AA:AA:AA"},
                {"ip_address": "192.168.99.98",
                 "mac_address": "AA:AA:AA:AA:AA:99"},
                {"ip_address": "192.168.98.96",
                 "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        # Send to IP2 and new mac2
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:99")

        # Send to IP2 and old mac2 - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:BB",
                                    should_fail=True)

        # Next update the allowed address pairs to REMOVE an entry
        port1 = self.api.update_port(port1['id'], {'port': {
            'allowed_address_pairs': [{
                "ip_address": "192.168.99.99",
                "mac_address": "AA:AA:AA:AA:AA:AA"},
                {"ip_address": "192.168.98.96",
                 "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        self.delete_security_group_rule(sgr99_98['id'])

        # Send to IP2 and mac2
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.96",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Send to IP1 and mac1
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:AA")

        # Send to deleted IP/mac - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.98",
                                    spoof_mac="AA:AA:AA:AA:AA:BB",
                                    should_fail=True)

        # Last, CLEAR all entries
        port1 = self.api.update_port(
            port1['id'],
            {'port': {
                'allowed_address_pairs': []}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        self.delete_security_group_rule(sgr99_99['id'])
        self.delete_security_group_rule(sgr98_96['id'])

        # Default IP/MAC should still work
        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to deleted IP/mac - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:AA",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_ip_subnet_with_specific_ip(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.0/24",),
                                   ("192.168.99.98",)],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.0/24')

        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to subnet IP with default MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.2",
                                    spoof_mac="", with_mac=False)

        # Send to specific IP with default MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="", with_mac=False)

        # Now update allowed pair list to ADD a new IP/MAC and make
        # sure that works
        port1 = self.api.update_port(
            port1['id'],
            {'port': {'allowed_address_pairs': [
                {"ip_address": "192.168.99.0/24"},
                {"ip_address": "192.168.99.98"},
                {"ip_address": "192.168.99.97",
                 "mac_address": "AA:AA:AA:AA:AA:DD"}]}})['port']
        self.LOG.debug('Updated port1: ' + str(port1))

        # Send to new specific IP with new MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.97",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Send to specific IP with default MAC (as a part of
        # the subnet definition)
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.97",
                                    spoof_mac="", with_mac=False)

        # Still can spoof to old IPs
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="", with_mac=False)

        # Send to old IP with new MAC - should FAIL
        self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                    receiver_ip=ip2,
                                    spoof_ip="192.168.99.99",
                                    spoof_mac="AA:AA:AA:AA:AA:DD",
                                    should_fail=True)

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_ip_subnet_with_mixed_ips_macs(self):
        aap_sg = self.create_security_group('aap_sg')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_group_id=aap_sg['id'])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            allowed_address_pairs=[("192.168.99.0/24",),
                                   ("192.168.99.98", "AA:AA:AA:AA:AA:DD"),
                                   ("192.168.98.0/24", "AA:AA:AA:AA:AA:CC"),
                                   ("192.168.98.5",)],
            sgs=[aap_sg['id']])
        (port2, vm2, ip2) = self.create_vm_server(
            'vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['gateway_ip'],
            sgs=[aap_sg['id']])

        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.99.0/24')
        self.create_security_group_rule(
            aap_sg['id'],
            direction='ingress',
            remote_ip_prefix='192.168.98.0/24')

        self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0', timeout=30))

        # Send to subnet, default MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.66",
                                    spoof_mac="", with_mac=False)

        # Send to subnet, spoof MAC - should fail
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.66",
                                    spoof_mac="AA:AA:AA:AA:AA:DD",
                                    should_fail=True)

        # Send to specific IP, spoofed MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="AA:AA:AA:AA:AA:DD")

        # Send to specific IP as part of subnet, default MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.99.98",
                                    spoof_mac="", with_mac=False)

        # Send to subnet, spoofed MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.77",
                                    spoof_mac="AA:AA:AA:AA:AA:CC")

        # Send to subnet IP, default MAC - should fail
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.77",
                                    spoof_mac="", with_mac=False,
                                    should_fail=True)

        # Send to specific IP, default MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.5",
                                    spoof_mac="", with_mac=False)

        # Send to specific IP as part of subnet, spoofed MAC
        self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2,
                                    spoof_ip="192.168.98.5",
                                    spoof_mac="AA:AA:AA:AA:AA:CC")

    @require_extension("allowed-address-pairs")
    def test_allowed_address_pairs_error(self):
        # Allowed address pair must have IP address
        try:
            self.api.create_port(
                {'port': {'name': 'port1',
                          'network_id': self.main_network['id'],
                          'admin_state_up': True,
                          'allowed_address_pairs': [
                              {"mac_address": "AA:AA:AA:AA:AA:AA"}
                          ],
                          'tenant_id': 'admin'}})['port']
        except BadRequest:
            pass
        else:
            self.fail(
                "Should have thrown BadRequest when IP Address is missing.")
