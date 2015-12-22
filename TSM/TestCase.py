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
import importlib
import logging
import datetime

from common.Exceptions import *


from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager


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

    def run(self, result=None):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('Running test case: ' + self._get_name() + ' - ' + self._testMethodName)
        try:
            super(TestCase, self).run(result)
            self.LOG.info('Test case finished: ' + self._get_name() + ' - ' + self._testMethodName)
        finally:
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def debug(self):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('Running test case: ' + self._get_name() + ' - ' + self._testMethodName)
        try:
            super(TestCase, self).debug()
            self.LOG.info('Test case finished: ' + self._get_name() + ' - ' + self._testMethodName)
        except Exception as e:
            self.LOG.fatal('Test case error: ' + self._get_name() + ' - ' + self._testMethodName + ": " + str(e))
            raise e
        finally:
            self.stop_time = datetime.datetime.utcnow()
            self.run_time = (self.stop_time - self.start_time)

    def set_logger(self, log, console=None):
        self.LOG = log
        self.CONSOLE = console

    def runTest(self):
        pass


class expected_failure(object):
    def __init__(self, issue_id):
        self.issue_id = issue_id

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :param slf: TestCase
            """
            try:
                f(slf, *args)
                slf.fail('Expected failure (see issue: ' + str(self.issue_id) +
                         ') did not fail!  Remove "expected_failure" annotation?')
            except:
                slf.skipTest('Expected failure (see issue: ' + str(self.issue_id) + ')')

        return new_tester
