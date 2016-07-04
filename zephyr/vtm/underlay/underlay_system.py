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

import logging
from zephyr.common import exceptions
from zephyr.common import zephyr_constants as z_con


class UnderlaySystem(object):
    global_vm_id = 0

    def __init__(self, debug=False, log_manager=None,
                 log_file=z_con.ZEPHYR_LOG_FILE_NAME):
        self.hosts = {}
        self.log_dir = '.'
        self.debug = debug
        self.log_manager = log_manager
        self.hypervisors = {}
        self.log_file_name = log_file
        self.log_level = (logging.DEBUG
                          if debug is True
                          else logging.INFO)

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(
                file_name=self.log_file_name,
                name='underlay-system-debug',
                file_log_level=self.log_level,
                stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(
                file_name=self.log_file_name,
                name='underlay-system',
                log_level=self.log_level)

    def read_config(self, config_map):
        self.log_dir = config_map.get('log_dir', '.')

    def get_topology_feature(self, name):
        return None

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        pass

    def provision_vm_on_most_open_hv(
            self, hv_map, vm_count_fn,
            ip_addr, mac=None, gw_ip=None, name=None,
            requested_host=None):
        """
        :type hv_map: dict[str, UnderlayHost]
        :type vm_count_fn: runnable
        :type ip_addr: str
        :type mac: str
        :type gw_ip: str
        :type name: str
        :type requested_host: str | list[str]
        """
        self.LOG.debug(
            "Attempting to provision VM with IP: " + str(ip_addr) +
            (' on host: ' + str(requested_host) if requested_host else '') +
            (' with name: ' + name if name else ''))

        if name is not None:
            requested_vm_name = name
        else:
            requested_vm_name = 'vm_' + str(self.global_vm_id)
            self.global_vm_id += 1

        valid_host_map = hv_map.copy()
        if requested_host:
            if not isinstance(requested_host, list):
                requested_host = [requested_host]
            first_positive = True
            for rh in requested_host:
                if rh.startswith('!'):
                    valid_host_map.pop(rh[1:])
                else:
                    if rh not in hv_map:
                        raise exceptions.ArgMismatchException(
                            "Cannot start VM, unknown hypervisor: " +
                            rh)

                    # If there is at least one requested host, then only
                    # include it in the list of possible hosts.  Further
                    # positive entries will add to this list, just as
                    # negative entries will remove them from the list.
                    if first_positive:
                        valid_host_map = {rh: hv_map[rh]}
                        first_positive = False
                    else:
                        valid_host_map[rh] = hv_map[rh]

        if len(valid_host_map) == 0:
            raise exceptions.ObjectNotFoundException(
                'No suitable hypervisor found to launch VM')

        start_hv_host = reduce(
            lambda a, b: a if vm_count_fn(a) <= vm_count_fn(b) else b,
            valid_host_map.values())
        return start_hv_host.create_vm(
            ip_addr=ip_addr, mac=mac, gw_ip=gw_ip, name=requested_vm_name)
