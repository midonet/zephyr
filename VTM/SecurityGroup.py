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

import json


class SecurityGroup(object):

    def __init__(self, id, name='', description='', tenant_id='', security_group_rules=None):
        """
        :type id: str
        :type name: str
        :type description: str
        :type tenant_id: str
        :type security_groups: list[SecurityGroupRule]
        :return:
        """
        self.id	= id
        self.name = name
        self.description = description
        self.tenant_id = tenant_id
        self.security_group_rules = security_group_rules

    def add_rule(self, rule):
        self.security_group_rules.append(rule)

    def from_json(config):
        obj = json.loads(config)
        sg_rules_map = config['security_group'] if 'security_group_rules' in obj else []
        new_rule_map = []
        for rule in sg_rules_map:
            new_rule_map.append(SecurityGroupRule.from_json(rule))
        return SecurityGroup(id=obj['id'] if 'id' in obj else '',
                             name=obj['name'] if 'name' in obj else '',
                             description=obj['description'] if 'description' in obj else '',
                             tenant_id=obj['tenant_id'] if 'tenant_id' in obj else '',
                             security_group_rules=
                             
                             SecurityGroupRulobj['security_group_rules'] if 'security_group_rules' in obj else {},
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


class SecurityGroupRule(object):
    def __init__(self, id, direction='', ethertype='', port_range_min=-1, port_range_max=-1, protocol='',
                 remote_group_id='', remote_ip_prefix='', security_group_id='', tenant_id=''):
        """
        :type id: str
        :type direction: str
        :type ethertype: str
        :type port_range_min: int
        :type port_range_max: int
        :type protocol: str
        :type remote_group_id: str
        :type remote_ip_prefix: str
        :type security_group_id: str
        :type tenant_id: str
        :return:
        """
        self.id = id
        self.direction = direction
        self.ethertype = ethertype
        self.port_range_max = port_range_max
        self.port_range_min = port_range_min
        self.protocol = protocol
        self.remote_group_id = remote_group_id
        self.remote_ip_prefix = remote_ip_prefix
        self.security_group_id = security_group_id
        self.tenant_id = tenant_id

    def from_json(config):
        obj = json.loads(config)
        return SecurityGroupRule(id=obj['id'] if 'id' in obj else '',
                                 direction=obj['direction'] if 'direction' in obj else '',
                                 ethertype=obj['ethertype'] if 'ethertype' in obj else '',
                                 port_range_max=obj['port_range_max'] if 'port_range_max' in obj else -1,
                                 port_range_min=obj['port_range_min'] if 'port_range_min' in obj else -1,
                                 protocol=obj['protocol'] if 'protocol' in obj else '',
                                 remote_group_id=obj['remote_group_id'] if 'remote_group_id' in obj else '',
                                 remote_ip_prefix=obj['remote_ip_prefix'] if 'remote_ip_prefix' in obj else '',
                                 security_group_id=obj['security_group_id'] if 'security_group_id' in obj else '',
                                 tenant_id=obj['tenant_id'] if 'tenant_id' in obj else '')

    @staticmethod
    def to_json(me):
        obj_map = {'id': me.id,
                   'direction': me.direction,
                   'ethertype': me.ethertype,
                   'port_range_max': me.port_range_max,
                   'port_range_min': me.port_range_min,
                   'protocol': me.protocol,
                   'remote_group_id': me.remote_group_id,
                   'remote_ip_prefix': me.remote_ip_prefix,
                   'security_group_id': me.security_group_id,
                   'tenant_id': me.tenant_id}
        return json.dumps(obj_map)

