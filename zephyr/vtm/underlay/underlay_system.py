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
from zephyr.common import zephyr_constants as z_con


class UnderlaySystem(object):
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
