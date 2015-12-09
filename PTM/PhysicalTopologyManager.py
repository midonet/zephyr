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

from PTM.PhysicalTopologyManagerImpl import PhysicalTopologyManagerImpl


class PhysicalTopologyManager(object):
    def __init__(self, impl=None):
        """
        Manage physical topology for test with the given impl as the actual PTM implementation.
        :type impl: PhysicalTopologyManagerImpl
        """
        super(PhysicalTopologyManager, self).__init__()
        self.impl_ = impl
        self.log_manager = self.impl_.log_manager
        self.root_dir = self.impl_.root_dir

    def configure(self, config_file, file_type='json'):
        """
        Configure the PTM with information from the given JSON file.

        IMPORTANT NOTE!!!  For Hosts and for Applications, the implementation class name
        in the [implementation] section MUST have the class's name be the same name as the
        last dotted-name in the module (the string after the last dot (.), without the
        .py extension)!

        :type file_name: str
        :return:
        """
        if self.impl_:
            self.impl_.configure(config_file, file_type)

    def print_config(self, indent=0, logger=None):
        if self.impl_:
            self.impl_.print_config(indent, logger)

    def startup(self):
        if self.impl_:
            self.impl_.startup()

    def shutdown(self):
        if self.impl_:
            self.impl_.shutdown()

    def create_vm(self, ip, mac=None, gw_ip=None, hv_host=None, name=None):
        if self.impl_:
            return self.impl_.create_vm(ip, mac, gw_ip, hv_host, name)
        return None

