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

class NeutronStubClientInterface(object):
    """ This class defines the interface functions the components in
        the Virtual Topology Manager need available from any client
        which will be used for the VTM system.  All clients must implement
        each of these functions in order to provide correct functionality
        to the VTM.

        Any client that derives from this interface is essentially taking
        the place of Neutron API, and so must provide the same entry points
        and accomplish similar tasks, although they do not have to implement
        their functions even remotely close to the Neutron implementation.
    """

    def __init__(self, *args, **kwargs):
        pass

    def list_ports(self):
        pass

    def list_networks(self):
        pass

    def delete_port(self, port):
        pass

    def delete_network(self, network):
        pass

    def show_subnet(self):
        pass


