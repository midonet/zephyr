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

from zephyr.common import exceptions
from zephyr.common import utils
from zephyr.vtm.underlay import direct_underlay_host
from zephyr.vtm.underlay import underlay_system


class DirectUnderlaySystem(underlay_system.UnderlaySystem):
    global_vm_id = 0

    def __init__(self, debug=False, logger=None):
        super(DirectUnderlaySystem, self).__init__(debug, logger)
        self.hosts = {}
        self.overlay_manager = None
        self.features = {
            "underlay_type": "direct"}

    def read_config(self, config_map):
        super(DirectUnderlaySystem, self).read_config(config_map)
        if 'overlay' not in config_map:
            raise exceptions.ArgMismatchException(
                "'overlay' MUST be specified in direct underlay config")
        ov_class = utils.get_class_from_fqn(config_map['overlay'])
        self.overlay_manager = ov_class()

        if 'hosts' not in config_map:
            raise exceptions.ArgMismatchException(
                "'hosts' MUST be specified in direct underlay config")

        for name, host in config_map["hosts"].iteritems():
            if name in self.hosts:
                raise exceptions.ArgMismatchException(
                    "A host should only be specified once: " + name)
            if "host_type" not in host:
                raise exceptions.ArgMismatchException(
                    "Each host should have a 'host_type' field.")
            if "vm_type" not in host:
                raise exceptions.ArgMismatchException(
                    "Each host should have a 'vm_type' field.")
            host_type = host["host_type"]
            vm_type = host["vm_type"]
            hypervisor = host.get("hypervisor", True)

            if host_type == "local":
                new_host = direct_underlay_host.DirectUnderlayHost(
                    name=name, overlay=self.overlay_manager,
                    vm_type=vm_type, hypervisor=hypervisor,
                    logger=self.LOG)
            elif host_type == "remote":
                # TODO(micucci): Make this a RemoteUnderlayHost
                new_host = direct_underlay_host.DirectUnderlayHost(
                    name=name, overlay=self.overlay_manager,
                    vm_type=vm_type, hypervisor=hypervisor,
                    logger=self.LOG)
            else:
                raise exceptions.ArgMismatchException(
                    "Unrecognized host type: " + host_type)

            self.hosts[name] = new_host

    def get_topology_feature(self, name):
        return self.features.get(name, None)

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        self.LOG.debug(
            "Attempting to provision VM with IP: " + str(ip_addr) +
            (' on host: ' + hv_host if hv_host else '') +
            (' with name: ' + name if name else ''))
        start_hv_host = None
        """
        :type: zephyr.vtm.underlay.direct_underlay_host.DirectUnderlayHost
        """
        if hv_host and hv_host not in self.hosts:
            raise exceptions.ArgMismatchException(
                "Cannot start VM, unknown hypervisor: " + hv_host)

        current_least_vm_count = -1
        if hv_host:
            start_hv_host = self.hosts[hv_host]
        else:
            for h, underlay_host in self.hosts.iteritems():
                vm_count = len(underlay_host.vms)
                if (vm_count < current_least_vm_count or
                        current_least_vm_count == -1):
                    current_least_vm_count = vm_count
                    start_hv_host = underlay_host

        if not start_hv_host:
            raise exceptions.ObjectNotFoundException(
                'No suitable hypervisor service application '
                'found to launch VM')

        if name is not None:
            requested_vm_name = name
        else:
            requested_vm_name = 'vm_' + str(self.global_vm_id)
            self.global_vm_id += 1

        return start_hv_host.create_vm(
            ip_addr=ip_addr, mac=mac, gw_ip=gw_ip, name=requested_vm_name)
