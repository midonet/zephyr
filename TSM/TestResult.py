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


class TestResult(unittest.TestResult):
    def __init__(self, scenario):
        super(TestResult, self).__init__()
        self.scenario = scenario
        self.log_list = None
        self.successes = []

    def addSuccess(self, test):
        super(TestResult, self).addSuccess(test)
        self.successes.append(test)

    def to_junit_xml(self):
        def format_tc(tc):
            tcclass = '.'.join(tc.id().split('.')[:-1])
            tcname = tc.id().split('.')[-1]
            return '  <testcase classname="{0}" name="{1}"/>\n'.format(tcclass, tcname)

        def format_tc_data(tc, data):
            tcclass = '.'.join(tc.id().split('.')[:-1])
            tcname = tc.id().split('.')[-1]
            return '  <testcase classname="{0}" name="{1}">\n    {2}\n  </testcase>\n'.format(tcclass, tcname, data)

        ts_str = '<testsuite errors="{errors:d}" failures="{failures:d}" name="{name}" tests="{tests:d}">\n'
        ret_xml = ts_str.format(errors=len(self.errors),
                                failures=len(self.failures) + len(self.unexpectedSuccesses),
                                name=self.scenario.__class__.__name__,
                                tests=self.testsRun)

        for tc in self.successes:
            ret_xml += format_tc(tc)

        for tc, data in self.failures:
            reason = 'Trace [' + data + ']'
            fail = '<failure type={0}>'.format(tc.failureException.__name__) + reason + '</failure>'
            ret_xml += format_tc_data(tc, fail)

        for tc in self.unexpectedSuccesses:
            reason = '<failure>Unexpected Success</failure>'
            ret_xml += format_tc_data(tc, reason)

        for tc, data in self.errors:
            reason = 'Trace [' + data + ']'
            err = '<error type={0}>'.format(tc.failureException.__name__) + reason + '</error>'
            ret_xml += format_tc_data(tc, err)

        for tc, data in self.skipped:
            reason = 'Trace [' + data + ']'
            info = '<skipped>' + data + '</skipped>'
            ret_xml += format_tc_data(tc, info)

        for tc, data in self.expectedFailures:
            reason = 'Trace [' + data + ']'
            info = '<skipped>Expected Failure: [' + tc.failureException.__name__ + '] ' + reason + '</skipped>'
            ret_xml += format_tc_data(tc, info)

        ret_xml += '</testsuite>\n'
        return ret_xml
