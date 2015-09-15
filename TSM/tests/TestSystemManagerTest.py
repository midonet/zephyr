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

from common.LogManager import LogManager

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

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)
        tsm.load_tests([SampleTestCase, SampleOtherTestCase])

        for i, tc in tsm.test_cases.iteritems():
            self.assertEqual(i, tc._get_name())
            self.assertFalse(isinstance(tc, TestCase))
            self.assertTrue(issubclass(tc, TestCase))

    def test_single_case_single_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        result = tsm.run_scenario(SampleTestScenario, [SampleOtherTestCase])

        self.assertEqual(SampleTestScenario, result.scenario)

        self.assertEqual(2, result.testsRun)
        self.assertEqual(1, len(result.failures))
        self.assertEqual(1, len(result.successes))
        self.assertEqual(0, len(result.errors))

    def test_single_case_multi_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        result1 = tsm.run_scenario(SampleTestScenario, [SampleTestCase])
        result2 = tsm.run_scenario(SampleOtherTestScenario, [SampleTestCase])

        self.assertEqual(SampleTestScenario, result1.scenario)
        self.assertEqual(SampleOtherTestScenario, result2.scenario)

        self.assertEqual(2, result1.testsRun)
        self.assertEqual(1, len(result1.failures))
        self.assertEqual(1, len(result1.successes))
        self.assertEqual(0, len(result1.errors))

        self.assertEqual(2, result2.testsRun)
        self.assertEqual(1, len(result2.failures))
        self.assertEqual(1, len(result2.successes))
        self.assertEqual(0, len(result2.errors))

    def test_double_case_multi_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        result1 = tsm.run_scenario(SampleTestScenario, [SampleTestCase, SampleOtherTestCase])
        result2 = tsm.run_scenario(SampleOtherTestScenario, [SampleTestCase, SampleOtherTestCase])

        self.assertEqual(SampleTestScenario, result1.scenario)
        self.assertEqual(SampleOtherTestScenario, result2.scenario)

        self.assertEqual(4, result1.testsRun)
        self.assertEqual(2, len(result1.failures))
        self.assertEqual(2, len(result1.successes))
        self.assertEqual(0, len(result1.errors))

        self.assertEqual(result1.successes[0].current_scenario.__class__, SampleTestScenario)
        self.assertEqual(result1.successes[0].__class__, SampleTestCase)
        self.assertEqual(result1.successes[1].current_scenario.__class__, SampleTestScenario)
        self.assertEqual(result1.successes[1].__class__, SampleOtherTestCase)

        self.assertEqual(2, result2.testsRun)
        self.assertEqual(1, len(result2.failures))
        self.assertEqual(1, len(result2.successes))
        self.assertEqual(0, len(result2.errors))

        self.assertEqual(result2.successes[0].current_scenario.__class__, SampleOtherTestScenario)
        self.assertEqual(result2.successes[0].__class__, SampleTestCase)

    def test_multi_case_multi_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test(SampleTestCase)
        tsm.add_test(SampleOtherTestCase)

        results = tsm.run_all_tests()

        self.assertIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)

        self.assertEqual(4, results[SampleTestScenario].testsRun)
        self.assertEqual(2, len(results[SampleTestScenario].failures))
        self.assertEqual(2, len(results[SampleTestScenario].successes))
        self.assertEqual(0, len(results[SampleTestScenario].errors))

        self.assertEqual(2, results[SampleOtherTestScenario].testsRun)
        self.assertEqual(1, len(results[SampleOtherTestScenario].failures))
        self.assertEqual(1, len(results[SampleOtherTestScenario].successes))
        self.assertEqual(0, len(results[SampleOtherTestScenario].errors))

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

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test(SampleTestCase)
        tsm.add_test(SampleOtherTestCase)

        results = tsm.run_all_tests([SampleOtherTestScenario])

        self.assertNotIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)

        self.assertEqual(2, results[SampleOtherTestScenario].testsRun)
        self.assertEqual(1, len(results[SampleOtherTestScenario].failures))
        self.assertEqual(1, len(results[SampleOtherTestScenario].successes))
        self.assertEqual(0, len(results[SampleOtherTestScenario].errors))


from CBT.UnitTestRunner import run_unit_test
run_unit_test(TestSystemManagerTest)


