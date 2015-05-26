__author__ = 'tomoe'
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

import neutronclient.neutron.client


class VirtualTopologyConfig(object):
    def __init__(self,
                 client_api_impl=neutronclient.neutron.client.Client,
                 endpoint_url='http://localhost:9696',
                 auth_strategy='noauth',
                 **kwargs):
        self.client_api_impl = client_api_impl(api_version='2.0',
                                               endpoint_url=endpoint_url,
                                               auth_strategy=auth_strategy,
                                               **kwargs)

    def clear(self):
        """Wipes out all the neutron resources
        """
        ports = self.client_api_impl.list_ports()
        for p in ports['ports']:
            self.client_api_impl.delete_port(p['id'])

        networks = self.client_api_impl.list_networks()
        for n in networks['networks']:
            self.client_api_impl.delete_network(n['id'])

    def get_client(self):
        return self.client_api_impl