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
from VTM.Subnet import Subnet

import json

class Network(object):
    def __init__(self, name, id, tenant_id, admin_state_up, status, subnets, shared):
        """
        :type name: str
        :type id: str
        :type tenant_id: str
        :type admin_state_up: bool
        :type status: str
        :type subnets: dict[str,Subnet]
        :type shared: bool
        """
        self.name = name
        self.tenant_id = tenant_id
        self.id = id
        self.ports = {}
        self.admin_state_up = admin_state_up
        self.status = status
        self.subnets = subnets
        self.shared = shared

    def get_subnet(self, subnet_id):
        if subnet_id not in self.subnets:
            raise ObjectNotFoundException('subnet: ' + subnet_id)
        return self.subnets[subnet_id]


    @staticmethod
    def from_json(config):
        obj = json.loads(config)
        return Network(name=obj['name'] if 'name' in obj else '',
                       id=obj['id'] if 'id' in obj else '',
                       tenant_id=obj['tenant_id'] if 'tenant_id' in obj else '',
                       admin_state_up=obj['admin_state_up'] if 'admin_state_up' in obj else False,
                       status=obj['status'] if 'status' in obj else '',
                       subnets=obj['subnets'] if 'subnets' in obj else {},
                       shared=obj['shared'] if 'shared' in obj else False)

    @staticmethod
    def to_json(me):
        obj_map = {'name': me.name,
                   'id': me.id,
                   'tenant_id': me.tenant_id,
                   'admin_state_up': me.admin_state_up,
                   'status': me.status,
                   'subnets': [s_id for s_id in me.subnets.iterkeys()],
                   'shared': me.shared}
        return json.dumps(obj_map)
