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
from tests.scenarios.Secnario_1z_1c_2m import Secnario_1z_1c_2m
from VTM.Guest import Guest

from  collections import namedtuple


class TestPortSecurity(NeutronTestCase):
    @staticmethod
    def supported_scenarios():
        return {Secnario_1z_1c_2m}

    def send_and_capture_spoof(self, sender, receiver, receiver_ip, with_mac=True,
                               spoof_ip='192.168.99.99', spoof_mac='AA:AA:AA:AA:AA:AA'):
        """
        :param sender: VMHost
        :param receiver: VMHost
        :param receiver_ip: str
        :return: list[PCAPPacket]
        """
        pcap_filter_list = [PCAP_ICMPProto(),
                            PCAP_Host(spoof_ip, proto='ip', source=True, dest=False)]
        if with_mac:
            pcap_filter_list.append(PCAP_Host(spoof_mac, proto='ether', source=True, dest=False))
        receiver.start_capture(on_iface='eth0', count=1,
                               filter=PCAP_And(pcap_filter_list))

        send_args = {'source_ip': spoof_ip, 'dest_ip': receiver_ip}
        if with_mac:
            send_args['source_mac'] = spoof_mac

        sender.send_packet(on_iface='eth0',
                           packet_type='icmp', packet_options={'command': 'ping'},
                           **send_args)

        try:
            return receiver.capture_packets(on_iface='eth0', count=1, timeout=3)
        finally:
            receiver.stop_capture(on_iface='eth0')

    def test_port_security_basic_normal_antispoof(self):
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

            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            # Default state should be PS enabled on net and any created ports
            # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
            packets = []
            try:
                packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2)
                self.fail('Spoofed packet should not have been received!')
            except SubprocessTimeoutException:
                pass

            # Next, add allowed address pair to the sender, but not receiver, so
            #   we can check a returning packet still gets blocked.  Also add the
            #   IP to the actual iface and the route so the return packet gets generated
            #   successfully (but still blocked at the neutron port)
            self.api.update_port(port1['id'],
                                 {'port': {'allowed_address_pairs': [{"ip_address": "192.168.99.99"}]}})

            vm2.execute('ip a add eth0 192.168.99.99')
            vm1.execute('ip r add 192.168.99.99/32 via ' + ip2)

            vm2.start_capture(on_iface='eth0', count=1,
                              filter=PCAP_And([PCAP_ICMPProto(),
                                               PCAP_Host('192.168.99.99', proto='ip', source=False, dest=True)]))

            self.assertFalse(vm1.ping(on_iface='eth0', target_ip=ip2))

            packets = vm2.capture_packets(on_iface='eth0', count=1, timeout=3)
            vm1.stop_capture(on_iface='eth0')

            # VM2 still should have received the ping, even if the reply didn't go through
            self.assertEqual(1, len(packets))

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

    def test_port_security_basic_disable_port(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            port1 = self.api.create_port({'port': {'name': 'port1',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'port_security_enabled': False,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port1: ' + str(port1))

            port2 = self.api.create_port({'port': {'name': 'port2',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'port_security_enabled': False,
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

            self.assertTrue(vm1.ping(on_iface='eth0', target_ip=ip2))

            # Disable port security
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])

            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

    def test_port_security_disable_entire_net(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None
        try:
            # Disable port security on entire network before creating ports
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

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

            packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2)])
            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

    def test_port_security_defaults_on_net(self):
        port1 = None
        port2 = None
        port3 = None
        port4 = None
        vm1 = None
        vm2 = None
        vm3 = None
        vm4 = None
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

            # Default state should be PS enabled on net and any created ports
            # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
            packets = []
            try:
                packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2)
                self.fail('Spoofed packet should not have been received!')
            except SubprocessTimeoutException:
                pass

            self.assertEqual(0, len(packets))

            # Next, let's disable PS on the network.  That should NOT affect currently
            #   created ports!
            self.LOG.debug("Disabling enabling port-security on main net")
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            # Should fail as port-security is still on for the current ports,
            #   so NO SPOOFING ALLOWED!
            try:
                packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2, receiver_ip=ip2)
                self.fail('Spoofed packet should not have been received!')
            except SubprocessTimeoutException:
                pass

            self.assertEqual(0, len(packets))

            self.LOG.debug("Creating ports on net with PS disabled")
            # New ports should be created with PS disabled
            port3 = self.api.create_port({'port': {'name': 'port3',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port3: ' + str(port3))

            port4 = self.api.create_port({'port': {'name': 'port4',
                                                   'network_id': self.main_network['id'],
                                                   'admin_state_up': True,
                                                   'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port4: ' + str(port4))

            ip3 = port3['fixed_ips'][0]['ip_address']
            ip4 = port4['fixed_ips'][0]['ip_address']

            vm3 = self.vtm.create_vm(ip=ip3, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""
            vm4 = self.vtm.create_vm(ip=ip4, gw_ip=self.main_subnet['gateway_ip'])
            """ :type: Guest"""

            vm3.plugin_vm('eth0', port3['id'], port3['mac_address'])
            vm4.plugin_vm('eth0', port4['id'], port4['mac_address'])

            # Should send okay because port and net security is disabled
            packets = self.send_and_capture_spoof(sender=vm3, receiver=vm4, receiver_ip=ip4)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

            # Now, re-enabling port security on the network shouldn't affect current ports
            self.LOG.debug("Re-enabling port-security on main net")
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            # Should still work, as ports were created when net security was disabled
            packets = self.send_and_capture_spoof(sender=vm3, receiver=vm4, receiver_ip=ip4)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.cleanup_vms([(vm1, port1), (vm2, port2), (vm3, port3), (vm4, port4)])
            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(self.main_network['id'],
                                    {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))
