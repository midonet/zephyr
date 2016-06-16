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


class UnderlaySystem(object):
    def __init__(self, debug=False, logger=None):
        self.hosts = {}
        self.log_dir = '.'
        self.debug = debug
        self.log_manager = None
        self.hypervisors = {}
        if logger:
            self.LOG = logger
        else:
            logging.getLogger('vtm-null-root')
            self.LOG.addHandler(logging.NullHandler())

    def read_config(self, config_map):
        self.log_dir = config_map.get('log_dir', '.')

    def get_topology_feature(self, name):
        return None

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        pass
