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
from TSM.TestSystemManager import TestSystemManager

from common.LogManager import LogManager


class TestSystemManagerTest(unittest.TestCase):
    def test_add_test_from_pkg_module_class(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase")
        self.assertEqual(1, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        self.assertIsNone(tc_pair[1])

    def test_add_test_from_pkg_module_class_multi(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase")
        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleOtherTestCase.test_basic")
        self.assertEqual(2, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        if tc_pair[0]._get_name() == "SampleOtherTestCase":
            self.assertEqual(1, len(tc_pair[1]))
            self.assertEqual("TSM.tests.sample.TestSampleCases.SampleOtherTestCase.test_basic", tc_pair[1].pop())
        else:
            self.assertIsNone(tc_pair[1])

        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        if tc_pair[0]._get_name() == "SampleOtherTestCase":
            self.assertEqual(1, len(tc_pair[1]))
            self.assertEqual("TSM.tests.sample.TestSampleCases.SampleOtherTestCase.test_basic", tc_pair[1].pop())
        else:
            self.assertIsNone(tc_pair[1])

    def test_add_test_from_pkg_module_class_func(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase.test_basic")
        self.assertEqual(1, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        self.assertEqual(1, len(tc_pair[1]))
        self.assertEqual(tc_pair[1].pop(), "TSM.tests.sample.TestSampleCases.SampleTestCase.test_basic")

    def test_add_test_from_pkg_module_class_func_multi(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase.test_basic")
        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase.test_a_failure")
        self.assertEqual(1, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        self.assertEqual(2, len(tc_pair[1]))
        self.assertIn(tc_pair[1].pop(), ["TSM.tests.sample.TestSampleCases.SampleTestCase.test_basic",
                                         "TSM.tests.sample.TestSampleCases.SampleTestCase.test_a_failure"])
        self.assertIn(tc_pair[1].pop(), ["TSM.tests.sample.TestSampleCases.SampleTestCase.test_basic",
                                         "TSM.tests.sample.TestSampleCases.SampleTestCase.test_a_failure"])

    def test_add_test_from_pkg_module(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases")
        self.assertEqual(2, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        self.assertIsNone(tc_pair[1])
        tc_pair2 = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair2[0], TestCase))
        self.assertIsNone(tc_pair2[1])

    def test_add_test_from_pkg(self):
        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample")
        self.assertEqual(2, len(tsm.test_cases))
        tc_pair = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair[0], TestCase))
        self.assertIsNone(tc_pair[1])
        tc_pair2 = tsm.test_cases.popitem()
        self.assertTrue(issubclass(tc_pair2[0], TestCase))
        self.assertIsNone(tc_pair2[1])

    def test_load_tests_from_classes_fqn(self):
        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.load_tests(["TSM.tests.sample.TestSampleCases.SampleTestCase",
                        "TSM.tests.sample.TestSampleCases.SampleOtherTestCase"])

        for test_class, func_list in tsm.test_cases.iteritems():
            self.assertTrue(issubclass(test_class, TestCase))

    def test_single_case_single_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        from TSM.tests.sample.TestSampleCases import SampleTestScenario, SampleOtherTestCase
        result = tsm.run_scenario(SampleTestScenario,
                                  [(SampleOtherTestCase,
                                    {"TSM.tests.sample.TestSampleCases.SampleOtherTestCase.test_basic"})
                                  ])

        self.assertEqual(SampleTestScenario, result.scenario)

        self.assertEqual(1, result.testsRun)
        self.assertEqual(0, len(result.failures))
        self.assertEqual(1, len(result.successes))
        self.assertEqual(0, len(result.errors))

    def test_single_case_multi_scenario_no_filter_no_topo(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        from TSM.tests.sample.TestSampleCases \
            import SampleTestScenario, SampleOtherTestScenario, SampleTestCase, SampleOtherTestCase
        result1 = tsm.run_scenario(SampleTestScenario, [(SampleTestCase, None)])
        result2 = tsm.run_scenario(SampleOtherTestScenario, [(SampleTestCase, None)])

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

        from TSM.tests.sample.TestSampleCases \
            import SampleTestScenario, SampleOtherTestScenario, SampleTestCase, SampleOtherTestCase
        result1 = tsm.run_scenario(SampleTestScenario,
                                   [(SampleTestCase, None), (SampleOtherTestCase, None)])
        result2 = tsm.run_scenario(SampleOtherTestScenario,
                                   [(SampleTestCase, None), (SampleOtherTestCase, None)])

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

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase")
        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleOtherTestCase")

        results = tsm.run_all_tests()

        from TSM.tests.sample.TestSampleCases \
            import SampleTestScenario, SampleOtherTestScenario

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

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase")
        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleOtherTestCase")

        from TSM.tests.sample.TestSampleCases \
            import SampleTestScenario, SampleOtherTestScenario

        results = tsm.run_all_tests([SampleOtherTestScenario])

        self.assertNotIn(SampleTestScenario, results)
        self.assertIn(SampleOtherTestScenario, results)

        self.assertEqual(2, results[SampleOtherTestScenario].testsRun)
        self.assertEqual(1, len(results[SampleOtherTestScenario].failures))
        self.assertEqual(1, len(results[SampleOtherTestScenario].successes))
        self.assertEqual(0, len(results[SampleOtherTestScenario].errors))

from CBT.UnitTestRunner import run_unit_test
run_unit_test(TestSystemManagerTest)


