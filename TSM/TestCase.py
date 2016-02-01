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

from common.Exceptions import *

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager


class EFException(unittest.case._ExpectedFailure):
    def __init__(self, exc_info, issue_id):
        super(EFException, self).__init__(exc_info)
        self.issue_id = issue_id


class TestCase(unittest.TestCase):

    vtm = None
    """ :type: VirtualTopologyManager"""
    ptm = None
    """ :type: PhysicalTopologyManager"""
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

        module = importlib.import_module(module_name if module_name != '' else class_name)
        impl_class = getattr(module, class_name)
        if not issubclass(impl_class, TestCase):
            raise ArgMismatchException('Class: ' + fqn + ' is not a subclass of TSM.TestCase')
        return impl_class

    @classmethod
    def _get_name(cls):
        return cls.__name__

    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        cls.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        cls.vtm = vtm
        """ :type: VirtualTopologyManager"""
        cls.LOG = test_case_logger
        if cls.LOG is None:
            cls.LOG = logging.getLogger(cls._get_name())

    def __init__(self, methodName='runTest'):
        super(TestCase, self).__init__(methodName)

        self.start_time = None
        """ :type: datetime.datetime"""
        self.stop_time = None
        """ :type: datetime.datetime"""
        self.run_time = None
        """ :type: datetime.timedelta"""
        self.expected_failure_issue_id = None
        """ :type: str"""

    def run(self, result=None):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('==========================================================================')
        self.LOG.info('Running test case: ' + self._get_name() + ' - ' + self._testMethodName)
        self.LOG.info('--------------------------------------------------------------------------')
        try:
            super(TestCase, self).run(result)
            self.LOG.info('Test case finished: ' + self._get_name() + ' - ' + self._testMethodName)
        except Exception as e:
            self.LOG.fatal('Test case exception: ' + self._get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        except AssertionError as e:
            self.LOG.fatal('Test case assertion error: ' + self._get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        finally:
            self.LOG.info('--------------------------------------------------------------------------')
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def debug(self):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('==========================================================================')
        self.LOG.info('Running test case: ' + self._get_name() + ' - ' + self._testMethodName)
        self.LOG.info('--------------------------------------------------------------------------')
        try:
            super(TestCase, self).debug()
            self.LOG.info('Test case finished: ' + self._get_name() + ' - ' + self._testMethodName)
        except Exception as e:
            self.LOG.fatal('Test case exception: ' + self._get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        except AssertionError as e:
            self.LOG.fatal('Test case assertion error: ' + self._get_name() + ' - ' +
                           self._testMethodName + ": " + str(e))
            raise e
        finally:
            self.LOG.info('--------------------------------------------------------------------------')
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def set_logger(self, log, console=None):
        self.LOG = log
        self.CONSOLE = console

    def runTest(self):
        pass

    def throw_expected_failure(self, issue_id):
        self.expected_failure_issue_id = issue_id
        raise unittest.case._ExpectedFailure(sys.exc_info())

    def ef_assertTrue(self, issue_id, condition, msg=None):
        try:
            self.assertTrue(condition, msg)
            self.fail('Expected failure passed (see issue: ' + str(issue_id) + ')')
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' + str(issue_id) + ')')
            self.throw_expected_failure(issue_id)

    def ef_assertFalse(self, issue_id, condition, msg=None):
        try:
            self.assertFalse(condition, msg)
            self.fail('Expected failure passed (see issue: ' + str(issue_id) + ')')
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' + str(issue_id) + ')')
            self.throw_expected_failure(issue_id)

    def ef_assertEqual(self, issue_id, a, b, msg=None):
        try:
            self.assertEqual(a, b, msg)
            self.fail('Expected failure passed (see issue: ' + str(issue_id) + ')')
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' + str(issue_id) + ')')
            self.throw_expected_failure(issue_id)

    def ef_assertIsNotNone(self, issue_id, condition, msg=None):
        try:
            self.assertIsNotNone(condition, msg)
            self.fail('Expected failure passed (see issue: ' + str(issue_id) + ')')
        except AssertionError:
            self.LOG.info('Expected failure (see issue: ' + str(issue_id) + ')')
            self.throw_expected_failure(issue_id)

    def ef_assertRaises(self, issue_id, excClass, callable=None, *args, **kwargs):
        try:
            self.assertRaises(excClass, callable, *args, **kwargs)
            self.fail('Expected failure passed (see issue: ' + str(issue_id) + ')')
        except AssertionError as e:
            self.LOG.info('Expected failure (see issue: ' + str(issue_id) + ')')
            self.throw_expected_failure(issue_id)


class expected_failure(object):
    def __init__(self, issue_id):
        self.issue_id = issue_id

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :type slf: TestCase
            """
            try:
                f(slf, *args)
                slf.fail('Expected failure passed (see issue: ' + str(self.issue_id) + ')')
            except:
                slf.LOG.info('Expected failure (see issue: ' + str(self.issue_id) + ')')
                slf.throw_expected_failure(self.issue_id)
        return new_tester


class require_topology_feature(object):
    def __init__(self, feature, func=None, value=None):
        self.feature = feature
        self.func = func
        self.value = value
    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :type slf: TestCase
            """
            feature_val = slf.ptm.get_topology_feature(self.feature)

            # If feature is set, func not set, value not set: Check for feature existence
            # If feature is set, func not set, value     set: Check feature == value
            # If feature is set, func     set, value not set: Check func(feature) == True
            # If feature is set, func     set, value     set: Check func(feature, value) == True
            # The latter is useful for operator.* functions like operator.lt and operator.gt
            if feature_val and \
                    ((self.func is     None and self.value is     None) or
                     (self.func is     None and self.value is not None and feature_val == self.value) or
                     (self.func is not None and self.value is     None and self.func(feature_val)) or
                     (self.func is not None and self.value is not None and self.func(feature_val, self.value))):
                f(slf, *args)
            else:
                slf.skipTest('Skipping because feature is not supported by the topology')
        return new_tester
