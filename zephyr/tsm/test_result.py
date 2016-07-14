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

import json
import unittest

from zephyr.tsm.test_case import TestCase


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
        return ([tc for tc in
                 self.successes + self.unexpectedSuccesses] +
                [tc[0] for tc in
                 (self.failures +
                  self.errors +
                  self.skipped +
                  self.expectedFailures)])

    def to_junit_xml(self):
        def format_tc(tcase):
            tcclass = '.'.join(tcase.id().split('.')[:-1])
            tcname = tcase.id().split('.')[-1]
            tcruntime = ('{0:d}.{1:d}'.format(tcase.run_time.seconds,
                                              tcase.run_time.microseconds)
                         if tcase.run_time is not None
                         else '0.0')
            return ('  <testcase classname="{0}" name="{1}" time="{2}"/>\n'
                    .format(tcclass, tcname, tcruntime))

        def format_tc_data(tcase, tdata):
            tcclass = '.'.join(tcase.id().split('.')[:-1])
            tcname = tcase.id().split('.')[-1]
            tcruntime = ('{0:d}.{1:d}'.format(tcase.run_time.seconds,
                                              tcase.run_time.microseconds)
                         if tcase.run_time is not None
                         else '0.0')
            return ('  <testcase classname="{0}" name="{1}" time="{2}">\n'
                    '    {3}\n'
                    '  </testcase>\n'
                    .format(tcclass, tcname, tcruntime, tdata))

        runtime = ('{0:d}.{1:d}'.format(self.run_time.seconds,
                                        self.run_time.microseconds)
                   if self.run_time is not None
                   else '0.0')
        ts_str = ('<testsuite '
                  'errors="{errors:d}" '
                  'failures="{failures:d}" '
                  'name="{name}" '
                  'tests="{tests:d}" '
                  'timestamp="{starttime}" '
                  'time="{runtime}">\n')
        ret_xml = ts_str.format(
            errors=len(self.errors),
            failures=len(self.failures) + len(self.unexpectedSuccesses),
            name=self.suite_name,
            tests=self.testsRun,
            starttime=(self.start_time.isoformat()
                       if self.start_time is not None
                       else '0.0'),
            runtime=runtime)

        for tc in self.successes:
            if isinstance(tc, TestCase):
                ret_xml += format_tc(tc)

        for tc, data in self.failures:
            ready_data = data.replace('<', '&lt;').replace('>', '&gt;')
            reason = 'Trace [' + ready_data + ']'
            if isinstance(tc, TestCase):
                if hasattr(tc.failureException, "__name__"):
                    report_str = tc.failureException.__name__
                else:
                    report_str = tc.failureException
                fail = ('<failure type="{0}">'.format(report_str) +
                        reason + '</failure>')
                ret_xml += format_tc_data(tc, fail)

        for tc in self.unexpectedSuccesses:
            reason = '<failure>Unexpected Success</failure>'
            if isinstance(tc, TestCase):
                ret_xml += format_tc_data(tc, reason)

        for tc, data in self.errors:
            ready_data = data.replace('<', '&lt;').replace('>', '&gt;')
            reason = 'Trace [' + ready_data + ']'
            if isinstance(tc, TestCase):
                if hasattr(tc.failureException, "__name__"):
                    report_str = tc.failureException.__name__
                else:
                    report_str = tc.failureException
                err = ('<error type="{0}">'.format(report_str) +
                       reason + '</error>')
                ret_xml += format_tc_data(tc, err)
            else:
                name = 'unknown'
                ret_xml += (
                    '<testcase name="' + name +
                    '-framework-error"><error type="FrameworkError">' +
                    reason + '</error></testcase>')

        for tc, data in self.skipped:
            if isinstance(tc, TestCase):
                ready_data = data.replace('<', '&lt;').replace('>', '&gt;')
                info = '<skipped>' + ready_data + '</skipped>'
                ret_xml += format_tc_data(tc, info)

        for tc, data in self.expectedFailures:
            ready_data = data.replace('<', '&lt;').replace('>', '&gt;')
            reason = 'Trace [' + ready_data + ']'
            if isinstance(tc, TestCase):
                if hasattr(tc.failureException, "__name__"):
                    report_str = tc.failureException.__name__
                else:
                    report_str = tc.failureException
                info = ('<skipped>Expected Failure: [' + report_str + '] ' +
                        reason + '</skipped>')
                ret_xml += format_tc_data(tc, info)

        ret_xml += '</testsuite>\n'
        return ret_xml

    def to_json(self):
        num_errors = len(self.errors)
        num_failures = len(self.failures) + len(self.unexpectedSuccesses)
        starttime = (self.start_time.isoformat()
                     if self.start_time is not None
                     else '0.0')
        runtime = ('{0:d}.{1:d}'.format(self.run_time.seconds,
                                        self.run_time.microseconds)
                   if self.run_time is not None
                   else '0.0')
        ts_map = {
            'testsuite': {
                'errors': num_errors,
                'failures': num_failures,
                'name': self.suite_name,
                'tests': self.testsRun,
                'timestamp': starttime,
                'time': runtime,
                'testcases': []
            }}

        tc_type_map = {
            'success': self.successes,
            'failure': self.failures,
            'skipped': self.skipped,
            'expected_failure': self.expectedFailures,
            'error': self.errors,
            'unexpected_success': self.unexpectedSuccesses
        }

        for ttype, tlist in tc_type_map.iteritems():
            for tparams in tlist:
                data = None
                if isinstance(tparams, tuple):
                    tc = tparams[0]
                    data = tparams[1]
                else:
                    tc = tparams

                if isinstance(tc, TestCase):
                    tcclass = '.'.join(tc.id().split('.')[:-1])
                    tcname = tc.id().split('.')[-1]
                    tcruntime = (
                        '{0:d}.{1:d}'.format(
                            tc.run_time.seconds,
                            tc.run_time.microseconds)
                        if tc.run_time is not None
                        else '0.0')
                    tc_start = tc.start_time.strftime('%Y-%m-%d %H:%M:%S,%f')
                    tc_stop = tc.stop_time.strftime('%Y-%m-%d %H:%M:%S,%f')
                    tc_map = {'type': ttype,
                              'classname': tcclass,
                              'name': tcname,
                              'runtime': tcruntime,
                              'starttime': tc_start,
                              'stoptime': tc_stop}
                    if data:
                        tc_map['data'] = data
                    ts_map['testsuite']['testcases'].append(tc_map)
                elif ttype == 'error':
                    ts_map['testsuite']['testcases'].append(
                        {'type': 'error',
                         'classname': "FrameworkError",
                         'name': "unknown-framework-error",
                         'runtime': '0.0',
                         'starttime': '0.0',
                         'stoptime': '0.0',
                         'data': data})

        return json.dumps(ts_map)
