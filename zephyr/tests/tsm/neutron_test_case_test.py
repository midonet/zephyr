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

import unittest

from zephyr.common.utils import run_unit_test
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.vtm import neutron_api
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager


class SampleTestCase(NeutronTestCase):
    @require_extension('agent')
    def test_needs_agent(self):
        pass

    @require_extension('asdf')
    def test_needs_asdf(self):
        self.fail("This test shouldn't be run!")


class NeutronTestCaseTest(unittest.TestCase):
    def test_require_extension(self):
        ptm = PhysicalTopologyManager()
        vtm = VirtualTopologyManager(
            None, neutron_api.create_neutron_client(), None)

        SampleTestCase._prepare_class(ptm, vtm)
        tc = SampleTestCase('test_needs_agent')
        tr = unittest.TestResult()
        tc.init_networks = False
        tc.run(tr)
        self.assertEqual(0, len(tr.errors))
        self.assertEqual(0, len(tr.failures))
        self.assertEqual(0, len(tr.failures))

        tc = SampleTestCase('test_needs_asdf')
        tr = unittest.TestResult()
        tc.init_networks = False
        tc.run(tr)
        self.assertEqual(0, len(tr.errors))
        self.assertEqual(1, len(tr.skipped))
        self.assertNotEqual(-1, str(
            tr.skipped[0][1]).find('Skipping because extension'))


run_unit_test(NeutronTestCaseTest)
