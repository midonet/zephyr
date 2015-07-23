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

from common.Exceptions import *
from TestScenario import TestScenario

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

class TestCase(unittest.TestCase):
    @staticmethod
    def supported_scenarios():
        """
        Subclasses should override to return a set of supported scenario classes
        :return: set[class]
        """
        return set()

    @classmethod
    def _get_name(cls):
        return cls.__name__

    def __init__(self, methodName='runTest'):
        super(TestCase, self).__init__(methodName)
        self.ptm = None
        """ :type: PhysicalTopologyManager"""
        self.vtm = None
        """ :type: VirtualTopologyManager"""
        self.current_scenario = None
        """ :type: class"""

    def _prepare(self, current_scenario):
        self.current_scenario = current_scenario
        """ :type: TestScenario"""
        self.ptm = self.current_scenario.ptm
        self.vtm = self.current_scenario.vtm

    def runTest(self):
        pass

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
