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
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.host import vm_host


class NetnsHV(application.Application):
    """
    A service to start and delete VMs represented by IP Net namespaces.
    """
    def __init__(self, host, app_id=''):
        super(NetnsHV, self).__init__(host, app_id)
        self.vms = {}

    @staticmethod
    def get_name():
        return 'netns_hv'

    @staticmethod
    def get_type():
        return application.APPLICATION_TYPE_HYPERVISOR

    @staticmethod
    def get_class_name():
        return ('zephyr_ptm.ptm.application.netns_hv.NetnsHV')

    def get_communication_ip(self):
        return self.host.main_ip

    def create_vm(self, name):
        """
        Create a VM and return it
        :type name: str
        :return: VMHost
        """
        new_host = vm_host.VMHost(name, self)
        new_host.configure_logging(
            log_file_name=self.log_file_name, debug=self.host.debug)
        new_host.create()
        new_host.boot()
        new_host.net_up()
        new_host.net_up()
        new_host.net_finalize()
        self.vms[name] = new_host
        return new_host

    def remove_vm(self, name):
        self.vms.pop(name)

    def get_vm(self, name):
        if name not in self.vms:
            raise exceptions.HostNotFoundException(name)
        return self.vms[name]

    def get_vm_count(self):
        return len(self.vms)

    def plugin_iface_to_network(self, vm_host_name, iface, port_id):
        net_type = application.APPLICATION_TYPE_NETWORK_OVERLAY
        if net_type not in self.host.applications_by_type:
            raise exceptions.ArgMismatchException(
                'Cannot plug in interface on host: ' + self.host.name +
                ' because there is no network overlay app running.')
        net_overlay_app = self.host.applications_by_type[net_type][0]
        net_overlay_app.connect_iface_to_port(
            vm_host_name=vm_host_name, iface=iface, port_id=port_id)

    def disconnect_port(self, port_id):
        net_type = application.APPLICATION_TYPE_NETWORK_OVERLAY
        if net_type not in self.host.applications_by_type:
            raise exceptions.ArgMismatchException(
                'Cannot plug in interface on host: ' + self.host.name +
                ' because there is no network overlay app running.')
        net_overlay_app = self.host.applications_by_type[net_type][0]
        net_overlay_app.disconnect_port(port_id)
