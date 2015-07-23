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

from TSM.TestCase import TestCase
from TSM.TestScenario import TestScenario
from TSM.TestSystemManager import TestSystemManager

class SampleTestScenario(TestScenario):
    def __init(self, ptm, vtm):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass


class SampleOtherTestScenario(TestScenario):
    def __init(self, ptm, vtm):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass


class SampleTestCase(TestCase):
    @staticmethod
    def supported_scenarios():
        return {SampleTestScenario, SampleOtherTestScenario}

    def test_basic(self):
        self.assertIn(self.current_scenario.__class__, self.supported_scenarios())
        pass

    def test_a_failure(self):
        self.assertFalse(True)
        pass


class SampleOtherTestCase(TestCase):
    @staticmethod
    def supported_scenarios():
        return {SampleTestScenario}

    def test_basic(self):
        self.assertIn(self.current_scenario.__class__, self.supported_scenarios())
        pass

    def test_a_failure(self):
        self.assertFalse(True)
        pass

class TestSystemManagerTest(unittest.TestCase):
    def test_load_tests(self):

        tsm = TestSystemManager(None, None)
        tsm.load_tests([SampleTestCase, SampleOtherTestCase])

        for i, tc in tsm.test_cases.iteritems():
            self.assertEquals(i, tc._get_name())
            self.assertFalse(isinstance(tc, TestCase))
            self.assertTrue(issubclass(tc, TestCase))

    def test_single_case_single_scenario_no_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        results = tsm.run_case(SampleOtherTestCase)
        self.assertIn(SampleTestScenario, results)
        self.assertEquals(2, results[SampleTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleTestScenario].failures))
        self.assertEquals(1, len(results[SampleTestScenario].successes))
        self.assertEquals(0, len(results[SampleTestScenario].errors))

    def test_single_case_multi_scenario_no_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        results = tsm.run_case(SampleTestCase)
        self.assertIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)
        self.assertEquals(2, results[SampleTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleTestScenario].failures))
        self.assertEquals(1, len(results[SampleTestScenario].successes))
        self.assertEquals(0, len(results[SampleTestScenario].errors))
        self.assertEquals(2, results[SampleOtherTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleOtherTestScenario].failures))
        self.assertEquals(1, len(results[SampleOtherTestScenario].successes))
        self.assertEquals(0, len(results[SampleOtherTestScenario].errors))

    def test_double_case_multi_scenario_no_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        results = tsm.run_case(SampleTestCase)
        results = tsm.run_case(SampleOtherTestCase)
        self.assertIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)
        self.assertEquals(4, results[SampleTestScenario].testsRun)
        self.assertEquals(2, len(results[SampleTestScenario].failures))
        self.assertEquals(2, len(results[SampleTestScenario].successes))
        self.assertEquals(0, len(results[SampleTestScenario].errors))
        self.assertEquals(2, results[SampleOtherTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleOtherTestScenario].failures))
        self.assertEquals(1, len(results[SampleOtherTestScenario].successes))
        self.assertEquals(0, len(results[SampleOtherTestScenario].errors))
        self.assertEquals(results[SampleTestScenario].successes[0].current_scenario.__class__,
                          SampleTestScenario)
        self.assertEquals(results[SampleTestScenario].successes[1].current_scenario.__class__,
                          SampleTestScenario)
        self.assertEquals(results[SampleOtherTestScenario].successes[0].current_scenario.__class__,
                          SampleOtherTestScenario)

    def test_double_case_multi_scenario_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        results = tsm.run_case(SampleTestCase, [SampleOtherTestScenario])
        results = tsm.run_case(SampleOtherTestCase, [SampleOtherTestScenario])
        self.assertNotIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)
        self.assertEquals(2, results[SampleOtherTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleOtherTestScenario].failures))
        self.assertEquals(1, len(results[SampleOtherTestScenario].successes))
        self.assertEquals(0, len(results[SampleOtherTestScenario].errors))
        self.assertEquals(results[SampleOtherTestScenario].successes[0].current_scenario.__class__,
                          SampleOtherTestScenario)

    def test_multi_case_multi_scenario_no_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        tsm.add_test(SampleTestCase)
        tsm.add_test(SampleOtherTestCase)
        results = tsm.run_all_tests()
        self.assertIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)
        self.assertEquals(4, results[SampleTestScenario].testsRun)
        self.assertEquals(2, len(results[SampleTestScenario].failures))
        self.assertEquals(2, len(results[SampleTestScenario].successes))
        self.assertEquals(0, len(results[SampleTestScenario].errors))
        self.assertEquals(2, results[SampleOtherTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleOtherTestScenario].failures))
        self.assertEquals(1, len(results[SampleOtherTestScenario].successes))
        self.assertEquals(0, len(results[SampleOtherTestScenario].errors))
        self.assertEquals(results[SampleTestScenario].successes[0].current_scenario.__class__,
                          SampleTestScenario)
        self.assertEquals(results[SampleTestScenario].successes[1].current_scenario.__class__,
                          SampleTestScenario)
        self.assertEquals(results[SampleOtherTestScenario].successes[0].current_scenario.__class__,
                          SampleOtherTestScenario)

        for s in results.iterkeys():
            print "========================================"
            print "Scenario [" + s.__name__ + "]"
            print "Passed [{0}/{1}]".format(len(results[s].successes), results[s].testsRun)
            print "Failed [{0}/{1}]".format(len(results[s].failures), results[s].testsRun)
            print "Error [{0}/{1}]".format(len(results[s].errors), results[s].testsRun)
            print ""
            for tc, err in results[s].failures:
                print "------------------------------"
                print "Test Case FAILED: [" + tc._get_name() + "]"
                print "Failure Message:"
                print err

            for tc, err in results[s].errors:
                print "------------------------------"
                print "Test Case ERROR: [" + tc._get_name() + "]"
                print "Error Message:"
                print err

    def test_multi_case_multi_scenario_filter_no_topo(self):
        tsm = TestSystemManager(None, None)
        tsm.add_test(SampleTestCase)
        tsm.add_test(SampleOtherTestCase)
        results = tsm.run_all_tests([SampleOtherTestScenario])
        self.assertNotIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)
        self.assertEquals(2, results[SampleOtherTestScenario].testsRun)
        self.assertEquals(1, len(results[SampleOtherTestScenario].failures))
        self.assertEquals(1, len(results[SampleOtherTestScenario].successes))
        self.assertEquals(0, len(results[SampleOtherTestScenario].errors))
        self.assertEquals(results[SampleOtherTestScenario].successes[0].current_scenario.__class__,
                          SampleOtherTestScenario)


try:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSystemManagerTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

