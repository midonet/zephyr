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

from common.Exceptions import InvallidConfigurationException
import json

class Port(object):
    def __init__(self, id, name='', network_id='', admin_state_up='', status='',
                 mac_address='', fixed_ips=list(), device_id='', device_owner='', tenant_id='',
                 security_groups=''):
        """
        :type id: str
        :type name: str
        :type network_id: str
        :type admin_state_up: bool
        :type status: str
        :type mac_address: str
        :type fixed_ips: list[str]
        :type device_id: str
        :type device_owner: str
        :type tenant_id: str
        :type security_groups: str
        :return:
        """
        self.id = id
        self.name = name
        self.network_id = network_id
        self.admin_state_up = admin_state_up
        self.status = status
        self.mac_address = mac_address
        self.fixed_ips = fixed_ips
        self.device_id = device_id
        self.device_owner = device_owner
        self.tenant_id = tenant_id
        self.security_groups = security_groups

    @staticmethod
    def from_json(config):
        obj = json.loads(config)
        return Port(name=obj['name'] if 'name' in obj else '',
                    tenant_id=obj['tenant_id'] if 'tenant_id' in obj else '',
                    id=obj['id'] if 'id' in obj else '',
                    network_id=obj['network_id'] if 'network_id' in obj else '',
                    admin_state_up=obj['admin_state_up'] if 'admin_state_up' in obj else False,
                    status=obj['status'] if 'status' in obj else '',
                    mac_address=obj['mac_address'] if 'mac_address' in obj else '',
                    fixed_ips=obj['fixed_ips'] if 'fixed_ips' in obj else [],
                    device_id=obj['device_id'] if 'device_id' in obj else '',
                    device_owner=obj['device_owner'] if 'device_owner' in obj else '')

    @staticmethod
    def to_json(me):
        obj_map = {'name': me.name,
                   'id': me.id,
                   'network_id': me.network_id,
                   'admin_state_up': me.admin_state_up,
                   'status': me.status,
                   'mac_address': me.mac_address,
                   'fixed_ips': me.fixed_ips,
                   'device_id': me.device_id,
                   'device_owner': me.device_owner}
        return json.dumps(obj_map)
