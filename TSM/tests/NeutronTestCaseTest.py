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

import unittest

from TSM.TestScenario import TestScenario
from TSM.NeutronTestCase import NeutronTestCase, require_extension
from TSM.fixtures.NeutronTestFixture import NeutronTestFixture
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.NeutronAPI import *


class SampleScenario(TestScenario):
    def setup(self):
        pass

    def teardown(self):
        pass


class SampleTestCase(NeutronTestCase):
    @staticmethod
    def supported_scenarios():
        return {SampleScenario}

    @require_extension('agent')
    def test_needs_agent(self):
        pass

    @require_extension('asdf')
    def test_needs_asdf(self):
        self.fail("This test shouldn't be run!")


class SampleFixture(NeutronTestFixture):
    def setup(self):
        pass

    def teardown(self):
        pass


class NeutronTestCaseTest(unittest.TestCase):
    def test_require_extension(self):
        vtm = VirtualTopologyManager(None, create_neutron_client(), None)
        scen = SampleScenario(None, vtm)
        scen.add_fixture('neutron-setup', SampleFixture(vtm, None, None))
        SampleTestCase._prepare_class(scen)
        tc = SampleTestCase('test_needs_agent')
        tr = unittest.TestResult()
        tc.run(tr)
        self.assertEquals(0, len(tr.errors))
        self.assertEquals(0, len(tr.failures))

        SampleTestCase._prepare_class(scen)
        tc = SampleTestCase('test_needs_asdf')
        tr = unittest.TestResult()
        tc.run(tr)
        self.assertEquals(0, len(tr.errors))
        self.assertEquals(1, len(tr.skipped))
        self.assertNotEqual(-1, str(tr.skipped[0][1]).find('Skipping because extension'))


from CBT.UnitTestRunner import run_unit_test
run_unit_test(NeutronTestCaseTest)


