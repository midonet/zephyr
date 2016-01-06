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

    def test_run_all_tests(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)


        tsm.load_tests(["TSM.tests.sample.TestSampleCases.SampleTestCase",
                        "TSM.tests.sample.TestSampleCases.SampleOtherTestCase"])

        result = tsm.run_all_tests('test1', 'foo-topo')

        self.assertEqual(4, result.testsRun)
        self.assertEqual(2, len(result.failures))
        self.assertEqual(2, len(result.successes))
        self.assertEqual(0, len(result.errors))

    def test_multi_suite_run(self):

        lm = LogManager(root_dir="test-logs")
        tsm = TestSystemManager(None, None, log_manager=lm)
        tsm.configure_logging(debug=True)

        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleTestCase")
        tsm.add_test("TSM.tests.sample.TestSampleCases.SampleOtherTestCase")

        tsm.run_all_tests('test1', 'foo-topo')
        tsm.run_all_tests('test2', 'foo-topo')
        results = tsm.result_map

        self.assertEqual(4, results['test1'].testsRun)
        self.assertEqual(2, len(results['test1'].failures))
        self.assertEqual(2, len(results['test1'].successes))
        self.assertEqual(0, len(results['test1'].errors))

        self.assertEqual(4, results['test2'].testsRun)
        self.assertEqual(2, len(results['test2'].failures))
        self.assertEqual(2, len(results['test2'].successes))
        self.assertEqual(0, len(results['test2'].errors))

        for s, r in results.iteritems():
            print "========================================"
            print "Scenario [" + s + "]"
            print "Passed [{0}/{1}]".format(len(r.successes), r.testsRun)
            print "Failed [{0}/{1}]".format(len(r.failures), r.testsRun)
            print "Error [{0}/{1}]".format(len(r.errors), r.testsRun)
            print ""
            for tc, err in r.failures:
                print "------------------------------"
                print "Test Case FAILED: [" + tc._get_name() + "]"
                print "Failure Message:"
                print err

            for tc, err in r.errors:
                print "------------------------------"
                print "Test Case ERROR: [" + tc._get_name() + "]"
                print "Error Message:"
                print err


from CBT.UnitTestRunner import run_unit_test
run_unit_test(TestSystemManagerTest)


