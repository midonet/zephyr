__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from VTM.NeutronStubClientInterface import NeutronStubClientInterface


class MNDirectClient(NeutronStubClientInterface):
    def __init__(self, *args, **kwargs):
        super(MNDirectClient, self).__init__(*args, **kwargs)
        self.subnet = {}
        self.options = {}
        if kwargs is not None:
            for k, v in kwargs.iteritems():
                self.options[k] = v
        pass

    def list_ports(self):
        pass

    def list_networks(self):
        pass

    def delete_port(self, port):
        pass

    def delete_network(self, network):
        pass

    def set_subnet(self, subnet):
        self.subnet = subnet

    def show_subnet(self):
        return self.subnet

    def get_option(self, key):
        if key in self.options:
            return self.options[key]
        return None