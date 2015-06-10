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

from VTM.VirtualTopologyConfig import VirtualTopologyConfig
from common.Exceptions import *

import json

class Subnet(object):
    def __init__(self, id, name, network_id, ip_version, cidr, gateway_ip,
                 dns_nameservers, allocation_pools, host_routes, enable_dhcp, tenant_id):
        """
        :type id: str
        :type name: str
        :type network_id: str
        :type ip_version: int
        :type cidr: str
        :type gateway_ip: str
        :type dns_nameservers: list[str]
        :type allocation_pools: list[dict[str,str]]
        :type host_routes: list[dict[str,str]]
        :type enable_dhcp: bool
        :type tenant_id: str
        """
        self.id = id
        self.name = name
        self.network_id = network_id
        self.ip_version = ip_version
        self.cidr = cidr
        self.gateway_ip = gateway_ip
        self.dns_nameservers = dns_nameservers
        self.allocation_pools = allocation_pools
        self.host_routes = host_routes
        self.enable_dhcp = enable_dhcp
        self.tenant_id = tenant_id
        self.ports = {}

    def get_port(self, port_id):
        if port_id in self.ports:
            return self.ports[port_id]
        return None

    def create_port(self):
        port = None
        port_id = ''
        self.ports[port_id] = port
        return port_id

    @staticmethod
    def from_json(config):
        obj = json.loads(config)
        return Subnet(id=obj['id'] if 'id' in obj else '',
                      name=obj['name'] if 'name' in obj else '',
                      network_id=obj['network_id'] if 'network_id' in obj else '',
                      ip_version=obj['ip_version'] if 'ip_version' in obj else 4,
                      cidr=obj['cidr'] if 'cidr' in obj else '',
                      gateway_ip=obj['gateway_ip'] if 'gateway_ip' in obj else '',
                      dns_nameservers=obj['dns_nameservers'] if 'dns_nameservers' in obj else [],
                      allocation_pools=obj['allocation_pools'] if 'allocation_pools' in obj else [],
                      host_routes=obj['host_routes'] if 'host_routes' in obj else [],
                      enable_dhcp=obj['enable_dhcp'] if 'enable_dhcp' in obj else False)

    @staticmethod
    def to_json(me):
        obj_map = {'id': me.id,
                   'name': me.name,
                   'network_id': me.network_id,
                   'ip_version': me.ip_version,
                   'cidr': me.cidr,
                   'gateway_ip': me.gateway_ip,
                   'dns_nameservers': me.dns_nameservers,
                   'allocation_pools': me.allocation_pools,
                   'host_routes': me.host_routes,
                   'enable_dhcp': me.enable_dhcp}
        return json.dumps(obj_map)
