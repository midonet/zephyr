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
    def __init__(self, id, name, network_id, admin_state_up, status,
                 mac_address, fixed_ips, device_id, device_owner, tenant_id):
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

    @staticmethod
    def from_json(config):
        if 'port' not in config:
            raise InvallidConfigurationException(config, 'no port')

        port_map = config['port']

        return Port(name = port_map['name'] if 'name' in port_map else '',
                    tenant_id = port_map['tenant_id'] if 'tenant_id' in port_map else '',
                    id = port_map['id'] if 'id' in port_map else '',
                    network_id = port_map['network_id'] if 'network_id' in port_map else '',
                    admin_state_up = port_map['admin_state_up'] if 'admin_state_up' in port_map else False,
                    status = port_map['status'] if 'status' in port_map else '',
                    mac_address = port_map['mac_address'] if 'mac_address' in port_map else '',
                    fixed_ips = port_map['fixed_ips'] if 'fixed_ips' in port_map else [],
                    device_id = port_map['device_id'] if 'device_id' in port_map else '',
                    device_owner = port_map['device_owner'] if 'device_owner' in port_map else '')

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
