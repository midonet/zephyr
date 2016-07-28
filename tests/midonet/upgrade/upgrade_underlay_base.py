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

import abc


class UpgradeUnderlayBase(object):
    def __init__(self):
        self.migrate_provider_router = False
        self.migrate_anti_spoof = False
        self.migrate_extra_routes = False

    def do_topo_prep(self):
        pass

    @abc.abstractmethod
    def start_vms(self):
        pass

    @abc.abstractmethod
    def do_migration(self, upgrader):
        pass

    def do_communication_test_pre(self):
        pass

    @abc.abstractmethod
    def do_communication_test_post(self):
        pass

    def do_topo_verify_pre(self):
        pass

    @abc.abstractmethod
    def do_topo_verify_post(self):
        pass
