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

from PTM.impl.PhysicalTopologyManagerImpl import PhysicalTopologyManagerImpl
from PTM.fixtures.ServiceFixture import ServiceFixture
from common.Exceptions import *


class PhysicalTopologyManager(object):
    def __init__(self, impl=None):
        """
        Manage physical topology for test with the given impl as the actual PTM implementation.
        :type impl: PhysicalTopologyManagerImpl
        """
        super(PhysicalTopologyManager, self).__init__()
        self.impl_ = impl
        self.log_manager = self.impl_.log_manager if self.impl_ and hasattr(self.impl_, "log_manager") else None
        self.root_dir = self.impl_.root_dir if self.impl_ and hasattr(self.impl_, "root_dir") else '.'
        self.fixtures = {}
        """ :type: dict[str, ServiceFixture]"""
        self.config_file = None

    def configure(self, config_file, file_type='json'):
        """
        Configure the PTM with information from the given JSON file.

        :type file_name: str
        :return:
        """
        self.config_file = config_file
        if self.impl_:
            self.impl_.configure(config_file, file_type)

    def print_config(self, indent=0, logger=None):
        if self.impl_:
            self.impl_.print_config(indent, logger)

    def print_features(self, logger=None):
        header_list = ['feature', 'value']
        print_list = []
        max_str_size = map(len, header_list)
        if self.impl_:
            #max_str_size = map(max, max_str_size, self.impl_.get_topology_features())
            for feat, val in self.get_topology_features().iteritems():
                print_list.append((str(feat), str(val)))
                max_str_size[0] = len(str(feat)) if len(str(feat)) > max_str_size[0] else max_str_size[0]
                max_str_size[1] = len(str(val)) if len(str(val)) > max_str_size[1] else max_str_size[1]
        print("Supported features of this PTM:")
        for feat, val in print_list:
            print(feat + ' = ' + str(val))

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

    def add_fixture(self, name, fixture):
        """
        Add a ServiceFixture to setup and tear down this scenario in addition to standard
        setup() and teardown() functions defined in scenario subclasses (most notably,
        this is useful when a certain batch of tests have specialized scenario needs
        that aren't suitable to create a hard dependency to the scenario subclass, such
        as virtual topology requirements, etc.).  The fixtures are added by name so they
        can be checked and accessed at a later time (or only set to be included once from
        many sources, etc.)
        :type name: str
        :type fixture: ServiceFixture
        """
        if fixture:
            self.fixtures[name] = fixture

    def fixture_setup(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: ServiceFixture"""
            fix.setup()

    def fixture_teardown(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: ServiceFixture"""
            fix.teardown()

    def get_fixture(self, name):
        if name in self.fixtures:
            return self.fixtures[name]
        raise ObjectNotFoundException('No fixture defined in scenario: ' + name)

    def get_topology_features(self):
        """
        :return: dict[str, any]
        """
        if self.impl_:
            ret_map = self.impl_.get_topology_features()
            """ :type: dict[str,str]"""
            ret_map.update({'config_file': self.config_file})
        return ret_map

    def get_topology_feature(self, feature):
        """
        Known topology features across all PTM types:

        compute_hosts: Number of compute nodes in the topology

        :type feature: str
        :return: any
        """
        if feature == 'config_file':
            return self.config_file
        if self.impl_:
            feat_map = self.impl_.get_topology_features()
            if feature in feat_map:
                return feat_map[feature]
            return None
