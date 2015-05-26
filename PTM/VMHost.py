__author__ = 'micucci'
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

from Host import Host


class VMHost(Host):
    def __init__(self, name, cli, host_create_func, host_remove_func, root_host):
        super(VMHost, self).__init__(name, cli, host_create_func, host_remove_func, root_host)

    def start(self):
        pass

    def stop(self):
        pass

    def plugin_iface(self, iface, port_id):
        self.root_host.connect_iface_to_port(self.name, iface, port_id)

    def unplug_iface(self, port_id):
        self.root_host.disconnect_port(port_id)

