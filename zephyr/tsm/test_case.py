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

import datetime
import importlib
import logging
import sys
import unittest
from zephyr.common.exceptions import ArgMismatchException


class EFException(unittest.case._ExpectedFailure):  # noqa
    def __init__(self, exc_info, issue_id):
        super(EFException, self).__init__(exc_info)
        self.issue_id = issue_id


class TestCase(unittest.TestCase):

    vtm = None
    """ :type: zephyr.vtm.virtual_topology_manager.VirtualTopologyManager"""
    underlay = None
    """ :type: zephyr.vtm.underlay.underlay_system.UnderlaySystem"""
    LOG = None
    """ :type: logging.Logger"""

    @staticmethod
    def get_class(fqn):
        """
        Return the class from the fully-qualified package/module/class name
        :type fqn: str
        :return:
        """
        class_name = fqn.split('.')[-1]
        module_name = '.'.join(fqn.split('.')[0:-1])

        module = importlib.import_module(module_name
                                         if module_name != '' else class_name)
        impl_class = getattr(module, class_name)
        if not issubclass(impl_class, TestCase):
            raise ArgMismatchException('Class: ' + fqn +
                                       ' is not a subclass of tsm.TestCase')
        return impl_class

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def _prepare_class(cls, vtm, test_case_logger=logging.getLogger()):
        cls.vtm = vtm
        cls.underlay = vtm.underlay_system if vtm else None
        """ :type: VirtualTopologyManager"""
        cls.LOG = test_case_logger
        if cls.LOG is None:
            cls.LOG = logging.getLogger(cls.get_name())

    def __init__(self, method_name='runTest'):
        super(TestCase, self).__init__(method_name)

        self.start_time = None
        """ :type: datetime.datetime"""
        self.stop_time = None
        """ :type: datetime.datetime"""
        self.run_time = None
        """ :type: datetime.timedelta"""
        self.expected_failure_issue_ids = []
        """ :type: list[str]"""
        self.current_result = None
        """ :type: unittest.TestResult"""

    def run(self, result=None):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('==================================================='
                      '=======================')
        self.LOG.info('Running test case: ' + self.get_name() + ' - ' +
                      self._testMethodName)
        self.LOG.info('---------------------------------------------------'
                      '-----------------------')
        try:
            self.current_result = result
            super(TestCase, self).run(result)
            self.LOG.info('Test case finished: ' + self.get_name() + ' - ' +
                          self._testMethodName)
        except Exception as e:
            self.LOG.fatal('Test case exception: ' + self.get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        except AssertionError as e:
            self.LOG.fatal('Test case assertion error: ' +
                           self.get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        finally:
            self.LOG.info('-----------------------------------------------'
                          '---------------------------')
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def debug(self):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('==================================================='
                      '=======================')
        self.LOG.info('Running test case: ' + self.get_name() + ' - ' +
                      self._testMethodName)
        self.LOG.info('---------------------------------------------------'
                      '-----------------------')
        try:
            super(TestCase, self).debug()
            self.LOG.info('Test case finished: ' + self.get_name() + ' - ' +
                          self._testMethodName)
        except Exception as e:
            self.LOG.fatal('Test case exception: ' + self.get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        except AssertionError as e:
            self.LOG.fatal('Test case assertion error: ' +
                           self.get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        finally:
            self.LOG.info('-----------------------------------------------'
                          '---------------------------')
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def set_logger(self, log, console=None):
        self.LOG = log
        self.CONSOLE = console

    def runTest(self):
        pass

    def add_expected_failure(self, issue_id, stop_on_fail=False):
        """
        Add an expected failure to the TestResult and also add the
        issue_id to the expected_failure_issue list so we can keep
        track.
        """
        self.expected_failure_issue_ids.append(issue_id)

        if stop_on_fail:
            raise unittest.case._ExpectedFailure(sys.exc_info())

        add_expected_failure = getattr(self._resultForDoCleanups,
                                       'addExpectedFailure', None)
        if add_expected_failure is not None:
            add_expected_failure(self, sys.exc_info())

    def ef_assertTrue(self, issue_id, condition, msg=None,
                      stop_on_fail=False):
        try:
            self.assertTrue(condition, msg)
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' +
                          str(issue_id) + ')')
            self.add_expected_failure(issue_id, stop_on_fail)
        else:
            self.fail('Expected failure passed (see issue: ' +
                      str(issue_id) + ')')

    def ef_assertFalse(self, issue_id, condition, msg=None,
                       stop_on_fail=False):
        try:
            self.assertFalse(condition, msg)
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' +
                          str(issue_id) + ')')
            self.add_expected_failure(issue_id, stop_on_fail)
        else:
            self.fail('Expected failure passed (see issue: ' +
                      str(issue_id) + ')')

    def ef_assertEqual(self, issue_id, a, b, msg=None,
                       stop_on_fail=False):
        try:
            self.assertEqual(a, b, msg)
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' +
                          str(issue_id) + ')')
            self.add_expected_failure(issue_id, stop_on_fail)
        else:
            self.fail('Expected failure passed (see issue: ' +
                      str(issue_id) + ')')

    def ef_assertIsNotNone(self, issue_id, condition, msg=None,
                           stop_on_fail=False):
        try:
            self.assertIsNotNone(condition, msg)
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' +
                          str(issue_id) + ')')
            self.add_expected_failure(issue_id, stop_on_fail)
        else:
            self.fail('Expected failure passed (see issue: ' +
                      str(issue_id) + ')')

    def ef_assertRaises(self, issue_id, exc_class, clble=None,
                        stop_on_fail=False, *args, **kwargs):
        try:
            self.assertRaises(exc_class, clble, *args, **kwargs)
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' +
                          str(issue_id) + ')')
            self.add_expected_failure(issue_id, stop_on_fail)
        else:
            self.fail('Expected failure passed (see issue: ' +
                      str(issue_id) + ')')


class expected_failure(object):  # noqa - Decorator class
    def __init__(self, issue_id):
        self.issue_id = issue_id

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :type slf: TestCase
            """
            try:
                f(slf, *args)
            except Exception:  # noqa No choice here, have to catch all
                slf.LOG.info('Expected failure (see issue: ' +
                             str(self.issue_id) + ')')
                slf.add_expected_failure(self.issue_id, stop_on_fail=True)
            else:
                slf.fail('Expected failure passed (see issue: ' +
                         str(self.issue_id) + ')')

        return new_tester


class require_topology_feature(object):  # noqa - Decorator class
    def __init__(self, feature, func=None, value=None):
        self.feature = feature
        self.func = func
        self.value = value

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :type slf: TestCase
            """
            feature_val = slf.underlay.get_topology_feature(self.feature)

            # If feature is set, func not set, value not set:
            # Check for feature existence
            # If feature is set, func not set, value     set:
            # Check feature == value
            # If feature is set, func     set, value not set:
            # Check func(feature) == True
            # If feature is set, func     set, value     set:
            # Check func(feature, value) == True
            # The latter is useful for operator.* functions like
            # operator.lt and operator.gt
            if (feature_val and
                ((self.func is None and self.value is None) or
                 (self.func is None and self.value is not None and
                    feature_val == self.value) or
                 (self.func is not None and self.value is None and
                    self.func(feature_val)) or
                 (self.func is not None and self.value is not None and
                    self.func(feature_val, self.value)))):
                f(slf, *args)
            else:
                slf.skipTest('Skipping because feature is not supported '
                             'by the topology')
        return new_tester


class require_hosts(object):  # noqa - Decorator class
    def __init__(self, hostnames, func=None, value=None):
        self.hostnames = hostnames
        self.func = func
        self.value = value

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :type slf: TestCase
            """
            if set(self.hostnames).issubset(slf.underlay.hosts):
                f(slf, *args)
            else:
                slf.skipTest(
                    'Skipping because hosts: ' + str(self.hostnames) +
                    ' are not all available (currently available hosts: ' +
                    str(slf.underlay.hosts.keys()) + ')')
        return new_tester
