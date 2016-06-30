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

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common import ip
from zephyr.common import utils
from zephyr.vtm.underlay import direct_underlay_host


class IPNetnsVM(direct_underlay_host.DirectUnderlayHost):
    def __init__(self, name, overlay, host, logger=None):
        super(IPNetnsVM, self).__init__(name, overlay, hypervisor=False,
                                        logger=logger)
        self.cli = cli.NetNSCLI(self.name)
        self.host = host
        self.main_iface_name = 'eth0'
        self.host_iface_name = self.name + self.main_iface_name

    def vm_startup(self, ip_addr, mac=None, gw_ip=None):
        cli.CREATENSCMD(self.name)
        peer_name = self.host_iface_name + '.p'

        self.LOG.debug("Creating VM interface: " + self.main_iface_name +
                       " and veth peer on hypervisor [" +
                       self.host.name + "] with name [" +
                       self.host_iface_name + "] and IP: " +
                       str(ip_addr))

        self.host.execute(
            'ip link add dev ' + self.host_iface_name +
            ' type veth peer name ' + peer_name)

        self.host.execute(
            'ip link set dev ' + peer_name + ' netns ' +
            self.name + ' name ' + self.main_iface_name)

        self.host.execute('ip link set dev ' + self.host_iface_name + ' up')
        self.execute('ip link set dev ' + self.main_iface_name + ' up')

        if mac is not None:
            self.execute('ip link set dev ' + self.main_iface_name +
                         ' address ' + mac)
        self.execute('ip addr add ' + str(ip.IP.make_ip(ip_addr)) +
                     ' dev ' + self.main_iface_name)

        if gw_ip is None:
            gw_ip = utils.make_gateway_ip(ip.IP.make_ip(ip_addr))

        self.LOG.debug("Adding default route for VM: " + gw_ip)
        self.add_route(gw_ip=ip.IP.make_ip(gw_ip))

    def create_vm(self, ip_addr, mac, gw_ip, name):
        raise exceptions.ArgMismatchException(
            "Cannot create a VM inside a VM.")

    def plugin_iface(self, iface, port_id):
        self.overlay.plugin_iface(self.host.unique_id,
                                  self.name + iface, port_id)

    def unplug_iface(self, port_id):
        self.overlay.unplug_iface(self.host.unique_id, port_id)

    def terminate(self):
        """
        Kill this Host.
        :return:
        """
        self.host.execute('ip link del dev ' + self.host_iface_name)
        cli.REMOVENSCMD(self.name)
        self.host.vms.pop(self.name)
