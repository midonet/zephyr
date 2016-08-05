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

import os

from zephyr.common import exceptions
from zephyr.common import zephyr_constants as z_con
from zephyr.vtm.underlay import underlay_system
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm import physical_topology_manager
from zephyr_ptm.ptm.underlay import ptm_underlay_host


class PTMUnderlaySystem(underlay_system.UnderlaySystem):

    def __init__(self, debug=False, log_manager=None,
                 log_file=z_con.ZEPHYR_LOG_FILE_NAME):
        super(PTMUnderlaySystem, self).__init__(
            debug=debug, log_manager=log_manager, log_file=log_file)
        self.ptm = None
        self.root_dir = '.'
        self.ptm_log_file = 'ptm-out.log'

    def read_config(self, config_map):
        super(PTMUnderlaySystem, self).read_config(config_map)

        self.root_dir = config_map.get('root_dir', '.')
        self.ptm_log_file = config_map.get('ptm_log_file', 'ptm-out.log')

        if 'topology_config_file' not in config_map:
            raise exceptions.ArgMismatchException(
                "'topology_config_file' MUST be in PTM underlay config")

        topo_config = config_map['topology_config_file']
        self.ptm = physical_topology_manager.PhysicalTopologyManager(
            root_dir=self.root_dir,
            log_manager=self.log_manager)
        self.ptm.configure_logging(
            log_file_name=self.ptm_log_file,
            debug=self.debug)
        self.ptm.configure(config_file=topo_config)

        self.hosts = {
            name: ptm_underlay_host.PTMUnderlayHost(
                name=name,
                host_obj=host)
            for name, host in self.ptm.hosts_by_name.items()}

        for hv in self.ptm.hypervisors.keys():
            if hv in self.hosts:
                self.hypervisors[hv] = self.hosts[hv]

    def create_vm(self, hv_host=None, name=None):
        def get_vm_count(item):
            app_type = application.APPLICATION_TYPE_HYPERVISOR
            host_obj = item.underlay_host_obj
            hv_app = next(iter(host_obj.applications_by_type[app_type]))
            return hv_app.get_vm_count()
        return self.provision_vm_on_most_open_hv(
            hv_map=self.hypervisors, vm_count_fn=get_vm_count,
            name=name, requested_host=hv_host)

    def get_topology_feature(self, name):
        if name == "underlay_type":
            return "ptm"
        if name == "auth_type":
            return "noauth"
        return self.ptm.get_topology_feature(name)
