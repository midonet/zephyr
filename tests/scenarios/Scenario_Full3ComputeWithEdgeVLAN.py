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

from TSM.TestScenario import TestScenario


class Scenario_Full3ComputeWithEdgeVLAN(TestScenario):
    def setup(self):
        self.ptm.configure(self.ptm.root_dir + '/config/ptm/3z-3c-3cass-4h-1edge+vlan.json')
        self.ptm.startup()

    def teardown(self):
        self.ptm.shutdown()