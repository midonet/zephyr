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
from zephyr.vtm.underlay import underlay_system


class DirectUnderlaySystem(underlay_system.UnderlaySystem):
    def read_config(self, config_map):
        super(DirectUnderlaySystem, self).read_config(config_map)
        if 'hosts' not in config_map:
            raise exceptions.ArgMismatchException(
                "'hosts' MUST be specified in direct underlay config")

    def get_topology_feature(self, name):
        pass

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        pass
