# Copyright 2016 Midokura SARL
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

import time
from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common import ip
from zephyr.common import utils
from zephyr.vtm.underlay import direct_underlay_host
from zephyr.vtm.underlay import vm_base


class IPNetnsVM(direct_underlay_host.DirectUnderlayHost,
                vm_base.VMBase):
    def __init__(self, name, overlay, host, logger=None):
        super(IPNetnsVM, self).__init__(name, overlay, hypervisor=False,
                                        logger=logger)
        self.cli = cli.NetNSCLI(self.name)
        self.host = host
        self.main_iface_name = 'eth0'

    def create_vm(self, name=None):
        raise exceptions.ArgMismatchException(
            "Cannot create a VM inside a VM.")

    def vm_startup(self, ip_addr=None, gw_ip=None):
        cli.CREATENSCMD(self.name)

        if ip_addr is not None:
            self.execute('ip addr add ' + str(ip.IP.make_ip(ip_addr)) +
                         ' dev ' + self.main_iface_name)
        else:
            self.get_ip_from_dhcp('eth0')

        if gw_ip is None:
            gw_ip = utils.make_gateway_ip(ip.IP.make_ip(ip_addr))

        self.LOG.debug("Adding default route for VM: " + gw_ip)
        self.add_route(gw_ip=ip.IP.make_ip(gw_ip))

    def setup_vm_network(self, ip_addr=None, gw_ip=None):
        pass

    def get_hypervisor_name(self):
        return self.hypervisor.name

    def plugin_port(self, iface, port_id, mac=None, vlans=None):
        tapname = 'tap' + port_id[0:8]
        self.hypervisor.create_tap_interface_for_vm(
            tap_iface_name=tapname, vm_host=self,
            vm_iface_name=iface, vm_mac=mac, vm_vlans=vlans)

        self.overlay.plugin_iface(self.host.unique_id,
                                  tapname, port_id)

    def unplug_port(self, port_id):
        self.overlay.unplug_iface(self.host.unique_id, port_id)

    def request_ip_from_dhcp(self, iface='eth0', timeout=10):
        file_name = self.name + '.' + iface
        self.cli.cmd(
            'dhclient -nw '
            '-pf /run/dhclient-' + file_name + '.pid '
            '-lf /var/lib/dhcp/dhclient-' + file_name + '.lease ' +
            iface)
        deadline = time.time() + timeout
        while not self.get_ip(iface):
            if time.time() > deadline:
                self.stop_dhcp_client(iface)
                raise exceptions.HostNotFoundException(
                    'No IP addr received from DHCP')
            time.sleep(0)

        ip_addr = self.get_ip(iface)
        self.dhcpcd_is_running.add(iface)
        self.LOG.debug("Received IP from DHCP server: " + ip_addr)
        return ip_addr

    def stop_dhcp_client(self, iface):
        if iface in self.dhcpcd_is_running:
            file_name = self.name + '.' + iface
            self.cli.cmd(
                'dhclient -r '
                '-pf /run/dhclient-' + file_name + '.pid '
                '-lf /var/lib/dhcp/dhclient-' + file_name + '.lease ' +
                iface)
            self.cli.rm('/run/dhclient-' + file_name + '.pid')
            self.cli.rm('/var/lib/dhcp/dhclient-' + file_name + '.lease')

    def terminate(self):
        """
        Kill this Host.
        :return:
        """
        self.host.remove_taps(self)
        cli.REMOVENSCMD(self.name)
        self.host.vms.pop(self.name)

        if self.main_iface_name in self.dhcpcd_is_running:
            self.stop_dhcp_client(self.main_iface_name)
