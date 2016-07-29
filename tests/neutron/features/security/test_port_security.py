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

from zephyr.common import exceptions
from zephyr.common.ip import IP
from zephyr.common import pcap
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension


class TestPortSecurity(NeutronTestCase):
    @staticmethod
    def send_and_capture_spoof(sender, receiver, receiver_ip,
                               with_mac=True, spoof_ip='192.168.99.99',
                               spoof_mac='AA:AA:AA:AA:AA:AA'):
        """
        :type sender: zephyr.vtm.guest.Guest
        :type receiver: zephyr.vtm.guest.Guest
        :type receiver_ip: str
        :return: list[PCAPPacket]
        """
        pcap_filter_list = [pcap.ICMPProto(),
                            pcap.Host(spoof_ip, proto='ip', source=True,
                                      dest=False)]
        if with_mac:
            pcap_filter_list.append(pcap.Host(spoof_mac, proto='ether',
                                              source=True, dest=False))
        receiver.start_capture(on_iface='eth0', count=1,
                               pfilter=pcap.And(pcap_filter_list))

        send_args = {'source_ip': spoof_ip, 'dest_ip': receiver_ip}
        if with_mac:
            send_args['source_mac'] = spoof_mac

        sender.send_packet(on_iface='eth0', packet_type='icmp',
                           packet_options={'command': 'ping'}, **send_args)

        try:
            return receiver.capture_packets(on_iface='eth0', count=1,
                                            timeout=3)
        finally:
            receiver.stop_capture(on_iface='eth0')

    @require_extension('port-security')
    def test_port_security_basic_normal_antispoof(self):
        new_ip1 = '192.168.99.99'
        new_ip2 = '192.168.99.235'
        port1, vm1, ip1 = self.create_vm_server(
            name='vm1', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['id'])
        port2, vm2, ip2 = self.create_vm_server(
            name='vm2', net_id=self.main_network['id'],
            gw_ip=self.main_subnet['id'])

        self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

        # Default state should be PS enabled on net and any created ports
        # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
        try:
            self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                        receiver_ip=ip2,
                                        with_mac=False,
                                        spoof_ip=new_ip1)
            self.fail('Spoofed packet should not have been received!')
        except exceptions.SubprocessTimeoutException:
            pass

        # Next, add new IPs to the sender and receiver, and add an allowed
        # address pair to the sender for its spoofed IP, but do NOT add the
        # new IP allowed pair to the receiver, so we can check a returning
        # packet still gets blocked.  Also add the IP to the actual iface
        # and the route so the return packet gets generated successfully
        # (but still blocked at the neutron port)

        vm2.vm_underlay.add_ip('eth0', new_ip2)

        vm1.vm_underlay.add_route(route_ip=IP(new_ip2, '32'),
                                  gw_ip=IP.make_ip(ip2))
        vm2.vm_underlay.add_route(route_ip=IP(new_ip1, '32'),
                                  gw_ip=IP.make_ip(ip1))

        self.api.update_port(
            port1['id'],
            {'port':
                {'allowed_address_pairs':
                 [{"ip_address": new_ip1}]}})

        vm2.start_echo_server(ip_addr=new_ip2)

        # Look for packets on the receiver from the spoofed new_ip1 address
        # to the new_ip2
        vm2.start_capture(on_iface='eth0', count=1,
                          pfilter=pcap.And([pcap.TCPProto(),
                                            pcap.Host(ip1, proto='ip',
                                                      source=True),
                                            pcap.Host(new_ip2, proto='ip',
                                                      dest=True)]))

        try:
            reply = vm1.send_echo_request(dest_ip=new_ip2)

            # No reply should make it all the way back
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        packets = vm2.capture_packets(on_iface='eth0', count=1, timeout=3)
        vm1.stop_capture(on_iface='eth0')

        # VM2 still should have received the ping, even if the reply
        # didn't go through
        self.assertEqual(1, len(packets))

    @require_extension('port-security')
    def test_port_security_basic_disable_port(self):
        try:
            port1, vm1, ip1 = self.create_vm_server(
                name='vm1', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'],
                port_security_enabled=False)
            port2, vm2, ip2 = self.create_vm_server(
                name='vm2', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'],
                port_security_enabled=False)

            self.assertTrue(vm1.verify_connection_to_host(vm2, use_tcp=False))

            # Disable port security
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                                  receiver_ip=ip2)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

    @require_extension('port-security')
    def test_port_security_disable_entire_net(self):
        try:
            # Disable port security on entire network before creating ports
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            port1, vm1, ip1 = self.create_vm_server(
                name='vm1', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])
            port2, vm2, ip2 = self.create_vm_server(
                name='vm2', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])

            packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                                  receiver_ip=ip2)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

    @require_extension('port-security')
    def test_port_security_defaults_on_net(self):
        try:
            port1, vm1, ip1 = self.create_vm_server(
                name='vm1', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])
            port2, vm2, ip2 = self.create_vm_server(
                name='vm2', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])

            # Default state should be PS enabled on net and any created ports
            # Should fail as port-security is still on, so NO SPOOFING ALLOWED!
            packets = []
            try:
                packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                                      receiver_ip=ip2)
                self.fail('Spoofed packet should not have been received!')
            except exceptions.SubprocessTimeoutException:
                pass

            self.assertEqual(0, len(packets))

            # Next, let's disable PS on the network.  That should NOT affect
            # currently created ports!
            self.LOG.debug("Disabling enabling port-security on main net")
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': False}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            # Should fail as port-security is still on for the current ports,
            #   so NO SPOOFING ALLOWED!
            try:
                packets = self.send_and_capture_spoof(sender=vm1, receiver=vm2,
                                                      receiver_ip=ip2)
                self.fail('Spoofed packet should not have been received!')
            except exceptions.SubprocessTimeoutException:
                pass

            self.assertEqual(0, len(packets))

            self.LOG.debug("Creating ports on net with PS disabled")
            # New ports should be created with PS disabled
            port3, vm3, ip3 = self.create_vm_server(
                name='vm3', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])
            port4, vm4, ip4 = self.create_vm_server(
                name='vm4', net_id=self.main_network['id'],
                gw_ip=self.main_subnet['id'])

            # Should send okay because port and net security is disabled
            packets = self.send_and_capture_spoof(sender=vm3, receiver=vm4,
                                                  receiver_ip=ip4)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

            # Now, re-enabling port security on the network shouldn't affect
            # current ports
            self.LOG.debug("Re-enabling port-security on main net")
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))

            # Should still work, as ports were created when net security was
            # disabled
            packets = self.send_and_capture_spoof(sender=vm3, receiver=vm4,
                                                  receiver_ip=ip4)
            """ :type: list[PCAPPacket]"""
            self.LOG.debug(packets[0].to_str())

            self.assertEqual(1, len(packets))

        finally:
            self.LOG.debug("Re-enabling port security on main network")
            self.api.update_network(
                self.main_network['id'],
                {'network': {'port_security_enabled': True}})
            net = self.api.show_network(self.main_network['id'])
            self.LOG.debug('net=' + str(net))
