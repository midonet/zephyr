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
from TSM.TestCase import TestCase


class SampleScenario(TestScenario):
    def setup(self):
        pass

    def teardown(self):
        pass


class SampleTestCase(TestCase):
    @staticmethod
    def supported_scenarios():
        return {SampleScenario}

    def test_basic(self):
        self.assertIs(self.current_scenario, SampleScenario)
        pass

    def test_a_failure(self):
        self.assertFalse(True)
        pass

class TestCaseTest(unittest.TestCase):
    def test_test_case_scenarios(self):
        tc = SampleTestCase()
        self.assertEquals('SampleTestCase', tc._get_name())
        self.assertIn(SampleScenario, tc.supported_scenarios())

    def test_test_case_run(self):
        tc = SampleTestCase('test_basic')
        tc._prepare(SampleScenario)
        tr = unittest.TestResult()
        tc.run(tr)
        self.assertEquals(0, len(tr.errors))
        self.assertEquals(0, len(tr.failures))

        tc = SampleTestCase('test_a_failure')
        tc._prepare(SampleScenario)
        tr = unittest.TestResult()
        tc.run(tr)
        self.assertEquals(0, len(tr.errors))
        self.assertEquals(1, len(tr.failures))


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCaseTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

