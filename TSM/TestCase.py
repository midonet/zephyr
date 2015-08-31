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
from TestScenario import TestScenario

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

class TestCase(unittest.TestCase):

    current_scenario = None
    """ :type: TestScenario"""
    vtm = None
    """ :type: VirtualTopologyManager"""
    ptm = None
    """ :type: PhysicalTopologyManager"""
    setup_logger = None
    """ :type: logging.Logger"""

    @staticmethod
    def supported_scenarios():
        """
        Subclasses should override to return a set of supported scenario classes
        :return: set[class]
        """
        return set()

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
    def _prepare_class(cls, current_scenario, tsm_logger=logging.getLogger()):
        cls.current_scenario = current_scenario
        cls.ptm = cls.current_scenario.ptm
        cls.vtm = cls.current_scenario.vtm
        cls.setup_logger = tsm_logger

    def __init__(self, methodName='runTest'):
        super(TestCase, self).__init__(methodName)

        self.LOG = None
        """ :type: logging.Logger"""
        self.CONSOLE = None
        """ :type: logging.Logger"""
        self.start_time = None
        """ :type: datetime.datetime"""
        self.stop_time = None
        """ :type: datetime.datetime"""
        self.run_time = None
        """ :type: datetime.datetime"""

    def run(self, result=None):
        self.start_time = datetime.datetime.utcnow()
        self.LOG.info('Running test case: ' + self._get_name() + ' - ' + self._testMethodName)
        super(TestCase, self).run(result)
        self.LOG.info('Test case finished: ' + self._get_name() + ' - ' + self._testMethodName)
        self.stop_time = datetime.datetime.utcnow()
        self.run_time = (self.stop_time - self.start_time)

    def set_logger(self, log, console=None):
        self.LOG = log
        self.CONSOLE = console

    def runTest(self):
        pass
