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

import importlib

from common.Exceptions import *
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from VTM.VirtualTopologyManager import VirtualTopologyManager

class TestScenario(object):
    def __init__(self, ptm, vtm):
        self.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        self.vtm = vtm
        """ :type: VirtualTopologyManager"""

    def setup(self):
        pass

    def teardown(self):
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

        print "fqn=" + fqn + "/classname=" + class_name

        module = importlib.import_module(module_name if module_name != '' else class_name)

        impl_class = getattr(module, class_name)
        if not issubclass(impl_class, TestScenario):
            raise ArgMismatchException('Class: ' + fqn + ' is not a subclass of TSM.TestCase')
        return impl_class