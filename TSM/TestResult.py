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
import datetime
import itertools
from TSM.TestCase import TestCase


class TestResult(unittest.TestResult):
    def __init__(self, suite_name):
        """
        :type suite_name:
        :return:
        """
        super(TestResult, self).__init__()
        self.suite_name = suite_name
        self.log_list = None
        self.successes = []
        self.start_time = None
        self.stop_time = None
        self.run_time = None

    def addSuccess(self, test):
        super(TestResult, self).addSuccess(test)
        self.successes.append(test)

    def all_tests(self):
        return [tc for tc in self.successes + self.unexpectedSuccesses] + \
               [tc[0] for tc in self.failures + self.errors + self.skipped + self.expectedFailures]

    def to_junit_xml(self):
        def format_tc(tc):
            tcclass = '.'.join(tc.id().split('.')[:-1])
            tcname = tc.id().split('.')[-1]
            tcruntime = '{0:d}.{1:d}'.format(tc.run_time.seconds, tc.run_time.microseconds) \
                if tc.run_time is not None else '0.0'
            return '  <testcase classname="{0}" name="{1}" time="{2}"/>\n'.format(tcclass, tcname, tcruntime)

        def format_tc_data(tc, data):
            tcclass = '.'.join(tc.id().split('.')[:-1])
            tcname = tc.id().split('.')[-1]
            tcruntime = '{0:d}.{1:d}'.format(tc.run_time.seconds, tc.run_time.microseconds) \
                if tc.run_time is not None else '0.0'
            return '  <testcase classname="{0}" name="{1}" time="{2}">\n' \
                   '    {3}\n' \
                   '  </testcase>\n'.format(tcclass, tcname, tcruntime, data)

        runtime = '{0:d}.{1:d}'.format(self.run_time.seconds, self.run_time.microseconds) \
            if self.run_time is not None else '0.0'
        ts_str = '<testsuite errors="{errors:d}" failures="{failures:d}" name="{name}" ' \
                            'tests="{tests:d}" timestamp="{starttime}" time="{runtime}">\n'
        ret_xml = ts_str.format(errors=len(self.errors),
                                failures=len(self.failures) + len(self.unexpectedSuccesses),
                                name=self.suite_name,
                                tests=self.testsRun,
                                starttime=self.start_time.isoformat() if self.start_time is not None else '0.0',
                                runtime=runtime)

        for tc in self.successes:
            if isinstance(tc, TestCase):
                ret_xml += format_tc(tc)

        for tc, data in self.failures:
            reason = 'Trace [' + data + ']'
            if isinstance(tc, TestCase):
                reportStr = ''
                if hasattr(tc.failureException, "__name__"):
                    reportStr = tc.failureException.__name__
                else:
                    reportStr = tc.failureException
                fail = '<failure type="{0}">'.format(reportStr) + reason + '</failure>'
                ret_xml += format_tc_data(tc, fail)

        for tc in self.unexpectedSuccesses:
            reason = '<failure>Unexpected Success</failure>'
            if isinstance(tc, TestCase):
                ret_xml += format_tc_data(tc, reason)

        for tc, data in self.errors:
            reason = 'Trace [' + data + ']'
            if isinstance(tc, TestCase):
                reportStr = ''
                if hasattr(tc.failureException, "__name__"):
                    reportStr = tc.failureException.__name__
                else:
                    reportStr = tc.failureException
                err = '<error type="{0}">'.format(reportStr) + reason + '</error>'
                ret_xml += format_tc_data(tc, err)
            else:
                name = 'unknown'
                ret_xml += '<testcase name="' + name + '-framework-error"><error type="FrameworkError">' + \
                           reason + '</error></testcase>'

        for tc, data in self.skipped:
            reason = 'Trace [' + data + ']'
            if isinstance(tc, TestCase):
                info = '<skipped>' + data + '</skipped>'
                ret_xml += format_tc_data(tc, info)

        for tc, data in self.expectedFailures:
            reason = 'Trace [' + data + ']'
            if isinstance(tc, TestCase):
                reportStr = ''
                if hasattr(tc.failureException, "__name__"):
                    reportStr = tc.failureException.__name__
                else:
                    reportStr = tc.failureException
                info = '<skipped>Expected Failure: [' + reportStr + '] ' + reason + '</skipped>'
                ret_xml += format_tc_data(tc, info)

        ret_xml += '</testsuite>\n'
        return ret_xml
