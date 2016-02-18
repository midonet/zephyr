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
import operator
from TSM.TestCase import expected_failure
from TSM.TestCase import require_topology_feature
from TSM.TestCase import TestCase
from PTM.impl.PhysicalTopologyManagerImpl import PhysicalTopologyManagerImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from CBT.UnitTestRunner import run_unit_test


class SamplePTM(PhysicalTopologyManagerImpl):
    def get_topology_features(self):
        return {'test_feature': True, 'test_number': 2}


class SampleTestCase(TestCase):
    def test_basic(self):
        pass

    def test_a_failure(self):
        self.assertFalse(True)

    @expected_failure('FOO')
    def test_expected_failure(self):
        self.assertFalse(True)
        self.assertFalse(True)

    def test_expected_failure_func(self):
        self.ef_assertFalse('BAR', True)

    def test_expected_failure_func_multi(self):
        self.ef_assertFalse('BAR', True)
        self.ef_assertFalse('BAZ', True)
        self.ef_assertFalse('BAMF', True)

    def test_expected_failure_func_with_fail(self):
        self.ef_assertFalse('BAR', True)
        self.assertTrue(False)

    def test_expected_failure_func_stop_on_fail(self):
        self.ef_assertFalse('BAR', True, stop_on_fail=True)
        self.assertTrue(False)


class SampleTopoFeatureTestCase(TestCase):
    @require_topology_feature('test_feature')
    def test_topology_feature_present(self):
        pass

    @require_topology_feature('test_feature', value=True)
    def test_topology_feature_with_bool_value(self):
        pass

    @require_topology_feature('test_number', value=2)
    def test_topology_feature_with_int_value(self):
        pass

    @require_topology_feature('test_feature', func=operator.ne, value=False)
    def test_topology_feature_with_func_bool(self):
        pass

    @require_topology_feature('test_number', func=operator.le, value=2)
    def test_topology_feature_with_func_int(self):
        pass

    @require_topology_feature('test_not_present_feature')
    def test_topology_feature_not_present(self):
        self.fail("Should have skipped this test")

    @require_topology_feature('test_feature', value=False)
    def test_topology_feature_not_equal_bool(self):
        self.fail("Should have skipped this test")

    @require_topology_feature('test_number', value=0)
    def test_topology_feature_not_equal_int(self):
        self.fail("Should have skipped this test")

    @require_topology_feature('test_feature', func=operator.ne, value=True)
    def test_topology_feature_func_fails_bool(self):
        self.fail("Should have skipped this test")

    @require_topology_feature('test_number', func=operator.gt, value=5)
    def test_topology_feature_func_fails_int(self):
        self.fail("Should have skipped this test")


class TestCaseTest(unittest.TestCase):
    def test_test_case_scenarios(self):
        tc = SampleTestCase()
        self.assertEqual('SampleTestCase', tc._get_name())

    def test_test_case_run(self):
        tc1 = SampleTestCase('test_basic')
        tc1._prepare_class(None, None, None)
        tr = unittest.TestResult()
        tc1.run(tr)
        self.assertEqual(0, len(tr.errors))
        self.assertEqual(0, len(tr.failures))

        tc2 = SampleTestCase('test_a_failure')
        tc2._prepare_class(None, None, None)
        tr = unittest.TestResult()
        tc2.run(tr)
        self.assertEqual(0, len(tr.errors))
        self.assertEqual(1, len(tr.failures))

    def test_expected_failures(self):
        tc1 = SampleTestCase('test_expected_failure')
        tc1._prepare_class(None, None, None)
        tr1 = unittest.TestResult()
        tc1.run(tr1)
        self.assertEqual(0, len(tr1.errors))
        self.assertEqual(0, len(tr1.failures))
        self.assertEqual(1, len(tr1.expectedFailures))
        res_tc, err = tr1.expectedFailures[0]
        self.assertEqual(1, len(res_tc.expected_failure_issue_ids))
        self.assertEqual('FOO', res_tc.expected_failure_issue_ids[0])

        tc2 = SampleTestCase('test_expected_failure_func')
        tc2._prepare_class(None, None, None)
        tr2 = unittest.TestResult()
        tc2.run(tr2)
        self.assertEqual(0, len(tr2.errors))
        self.assertEqual(0, len(tr2.failures))
        self.assertEqual(1, len(tr2.expectedFailures))
        res_tc2, err = tr2.expectedFailures[0]
        self.assertEqual(1, len(res_tc.expected_failure_issue_ids))
        self.assertEqual('BAR', res_tc2.expected_failure_issue_ids[0])

        tc3 = SampleTestCase('test_expected_failure_func_multi')
        tc3._prepare_class(None, None, None)
        tr3 = unittest.TestResult()
        tc3.run(tr3)
        self.assertEqual(0, len(tr3.errors))
        self.assertEqual(0, len(tr3.failures))
        self.assertEqual(3, len(tr3.expectedFailures))
        self.assertEqual(3, len(tc3.expected_failure_issue_ids))
        self.assertEqual('BAR', tc3.expected_failure_issue_ids[0])
        self.assertEqual('BAZ', tc3.expected_failure_issue_ids[1])
        self.assertEqual('BAMF', tc3.expected_failure_issue_ids[2])

        tc4 = SampleTestCase('test_expected_failure_func_with_fail')
        tc4._prepare_class(None, None, None)
        tr4 = unittest.TestResult()
        tc4.run(tr4)
        self.assertEqual(0, len(tr4.errors))
        self.assertEqual(1, len(tr4.failures))
        self.assertEqual(1, len(tr4.expectedFailures))
        self.assertEqual(1, len(tc4.expected_failure_issue_ids))
        self.assertEqual('BAR', tc4.expected_failure_issue_ids[0])

        tc4 = SampleTestCase('test_expected_failure_func_stop_on_fail')
        tc4._prepare_class(None, None, None)
        tr4 = unittest.TestResult()
        tc4.run(tr4)
        self.assertEqual(0, len(tr4.errors))
        self.assertEqual(0, len(tr4.failures))
        self.assertEqual(1, len(tr4.expectedFailures))
        self.assertEqual(1, len(tc4.expected_failure_issue_ids))
        self.assertEqual('BAR', tc4.expected_failure_issue_ids[0])

    def test_required_topology_feature(self):

        test_list = \
            [SampleTopoFeatureTestCase('test_topology_feature_present'),
             SampleTopoFeatureTestCase('test_topology_feature_with_bool_value'),
             SampleTopoFeatureTestCase('test_topology_feature_with_int_value'),
             SampleTopoFeatureTestCase('test_topology_feature_with_func_bool'),
             SampleTopoFeatureTestCase('test_topology_feature_with_func_int'),
             SampleTopoFeatureTestCase('test_topology_feature_not_present'),
             SampleTopoFeatureTestCase('test_topology_feature_not_equal_bool'),
             SampleTopoFeatureTestCase('test_topology_feature_not_equal_int'),
             SampleTopoFeatureTestCase('test_topology_feature_func_fails_bool'),
             SampleTopoFeatureTestCase('test_topology_feature_func_fails_int')]

        for t in test_list:
            t._prepare_class(PhysicalTopologyManager(SamplePTM()), None, None)

        tr = unittest.TestResult()

        for t in test_list:
            t.run(tr)

        self.assertEqual(10, tr.testsRun)
        self.assertEqual(0, len(tr.errors))
        self.assertEqual(0, len(tr.failures))
        self.assertEqual(5, len(tr.skipped))


run_unit_test(TestCaseTest)
