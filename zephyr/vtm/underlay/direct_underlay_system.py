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
from zephyr.common import zephyr_constants as z_con
from zephyr.vtm.underlay import direct_underlay_host
from zephyr.vtm.underlay import underlay_system


class DirectUnderlaySystem(underlay_system.UnderlaySystem):
    def __init__(self, debug=False, log_manager=None,
                 log_file=z_con.ZEPHYR_LOG_FILE_NAME):
        super(DirectUnderlaySystem, self).__init__(
            debug, log_manager, log_file)
        self.hosts = {}
        self.overlay_manager = None
        self.features = {
            "dhcp_on_vms": True,
            "underlay_type": "direct",
            "auth_type": "keystone"}

    def read_config(self, config_map):
        super(DirectUnderlaySystem, self).read_config(config_map)
        if 'overlay' not in config_map:
            raise exceptions.ArgMismatchException(
                "'overlay' MUST be specified in direct underlay config")
        overlay_map = config_map['overlay']
        if 'class' not in overlay_map:
            raise exceptions.ArgMismatchException(
                "'overlay' MUST have a 'class' specified in"
                " direct underlay config")

        ov_classname = overlay_map['class']
        ov_classargs = overlay_map.get('args', {})
        ov_class = utils.get_class_from_fqn(ov_classname)
        self.overlay_manager = ov_class(**ov_classargs)

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
            if "uuid" not in host:
                raise exceptions.ArgMismatchException(
                    "Each host should have a 'uuid' field.")

            host_type = host["host_type"]
            vm_type = host["vm_type"]
            hypervisor = host.get("hypervisor", True)
            unique_id = host['uuid']

            if host_type == "local":
                new_host = direct_underlay_host.DirectUnderlayHost(
                    name=name, unique_id=unique_id,
                    overlay=self.overlay_manager,
                    vm_type=vm_type, hypervisor=hypervisor,
                    logger=self.LOG)
            elif host_type == "remote":
                # TODO(micucci): Make this a RemoteUnderlayHost
                new_host = direct_underlay_host.DirectUnderlayHost(
                    name=name, unique_id=unique_id,
                    overlay=self.overlay_manager,
                    vm_type=vm_type, hypervisor=hypervisor,
                    logger=self.LOG)
            else:
                raise exceptions.ArgMismatchException(
                    "Unrecognized host type: " + host_type)

            self.hosts[name] = new_host

    def get_topology_feature(self, name):
        return self.features.get(name, None)

    def create_vm(self, mac=None, hv_host=None, name=None):
        def get_vm_count(item):
            return len(item.vms)

        return self.provision_vm_on_most_open_hv(
            hv_map=self.hosts, vm_count_fn=get_vm_count,
            mac=mac, name=name,
            requested_host=hv_host)
