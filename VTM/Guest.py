__author__ = 'tomoe'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import subprocess
from VTM.VirtualTopologyConfig import VirtualTopologyConfig
from PTM.VMHost import VMHost
from common.CLI import LinuxCLI

class Guest(object):
    """
    A class to wrap a VM from the Physical Topology Manager
    """

    def __init__(self, vtc, vm_host):
        self.vm_host = vm_host
        """ :type: VMHost"""
        self.vtc = vtc
        """ :type: VirtualTopologyConfig"""
        self.open_ports_by_interface = {}
        """ :type: dict[str, dict[str, Port]]"""

    def plugin_vm(self, iface, port):
        """ Links an interface on this VM to a virtual network port
            * bind interface to MidoNet with mm-ctl
        :type iface: str
        :type port: Port
        """

        try:
            self.vm_host.plugin_iface(iface, port.port_id)
            self.open_ports_by_interface[iface] = port

        except subprocess.CalledProcessError as e:
            print 'command output: ',   e.output
            raise

    def unplug_vm(self, port):
        """ Unlinks a port on this VM from the virtual network
        :param port: Port ID to unlink
        """

        try:
            self.vm_host.unplug_iface(port)
            self.open_ports_by_interface = {k: v for k, v in self.open_ports_by_interface if v != port}

        except subprocess.CalledProcessError as e:
            print 'command output: ',   e.output
            raise

    def send_arp_request(self, ip):
        return self.vm_host.send_arp_request('eth0', ip)

    def send_arp_reply(self, src_mac, target_mac, src_ip, target_ip):
        return self.vm_host.send_arp_reply('eth0', src_mac, target_mac, src_ip, target_ip)

    def clear_arp(self):
        return self.vm_host.flush_arp()

    def execute(self, cmdline, timeout=None):
        """Executes cmdline inside VM

        Args:
            cmdline: command line string that gets executed in this VM
            timeout: timeout in second

        Returns:
            output as a bytestring

        Raises:
            subprocess.CalledProcessError: when the command exists with non-zero
                                           value, including timeout.
            OSError: when the executable is not found or some other error
                     invoking
        """
        try:
            result = self.vm_host.cli.cmd(cmdline, timeout=timeout, return_output=True)
        except subprocess.CalledProcessError as e:
            print 'command output: ',   e.output
            raise

        return result

    def expect(self, pcap_filter_string, timeout):
        """
        Expects packet with pcap_filter_string with tcpdump.
        See man pcap-filter for more details as to what you can match.


        Args:
            pcap_filter_string: capture filter to pass to tcpdump
                                See man pcap-filter
            timeout: in second

        Returns:
            True: when packet arrives
            False: when packet doesn't arrive within timeout
        """

        count = 1
        cmdline = 'timeout %s tcpdump -n -l -i eth0 -c %s %s 2>&1' % (
            timeout,
            count, pcap_filter_string)

        try:
            output = self.execute(cmdline)
            retval = True
            for l in output.split('\n'):
                LOG.debug('output=%r', l)
        except subprocess.CalledProcessError as e:
            print 'OUTPUT: ', e.output
            LOG.debug('expect failed=%s', e)
            retval = False
        LOG.debug('Returning %r', retval)
        return retval

    def assert_pings_to(self, other, count=3):
        """
        Asserts that the sender VM can ping to the other VM

        :param other: ping target VM instance
        """


        sender = self._port['port'].get('fixed_ips')
        receiver = other._port['port'].get('fixed_ips')
        if sender and receiver:
            receiver_ip = receiver[0]['ip_address']
            try:
                self.execute('ping -c %s %s' % (count, receiver_ip))
            except:
                raise AssertionError(
                    'ping from %s to %s failed'% (self, other))

    def  __repr__(self):
        return 'VM(%s)(port_id=%s)' % (self._name, self._port['port']['id'])



