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
import logging

from common.Exceptions import *
from TSM.fixtures.TestFixture import TestFixture


class TestScenario(object):
    def __init__(self, ptm, vtm):
        self.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        self.vtm = vtm
        """ :type: VirtualTopologyManager"""
        self.fixtures = {}
        """ :type: dict[str, TestFixture]"""
        self.LOG = logging.getLogger('scen-null-root')
        self.LOG.addHandler(logging.NullHandler())
        """ :type: logging.Logger"""
        self.debug = False
        self.log_manager = self.ptm.log_manager if self.ptm else None

    def setup(self):
        pass

    def teardown(self):
        pass

    def configure_logging(self, log_name='scenario', debug=False, log_file_name='scenario.log'):
        self.debug = debug
        if self.log_manager is None:
            return

        if self.debug is True:
            scenario_log = self.log_manager.add_tee_logger(name=log_name + '-debug',
                                                           file_name=log_file_name,
                                                           file_log_level=logging.DEBUG,
                                                           stdout_log_level=logging.DEBUG)
            scenario_log.info('Starting debug logs')
        else:
            scenario_log = self.log_manager.add_file_logger(name=log_name,
                                                            file_name=log_file_name,
                                                            log_level=logging.INFO)
        self.LOG = scenario_log

    def add_fixture(self, name, fixture):
        """
        Add a TestFixture to setup and tear down this scenario in addition to standard
        setup() and teardown() functions defined in scenario subclasses (most notably,
        this is useful when a certain batch of tests have specialized scenario needs
        that aren't suitable to create a hard dependency to the scenario subclass, such
        as virtual topology requirements, etc.).  The fixtures are added by name so they
        can be checked and accessed at a later time (or only set to be included once from
        many sources, etc.)
        :type name: str
        :type fixture: TestFixture
        """
        if fixture:
            self.fixtures[name] = fixture

    def fixture_setup(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: TestFixture"""
            self.LOG.debug("Running fixture setup: " + name)
            fix.setup()

    def fixture_teardown(self):
        for name, fix in self.fixtures.iteritems():
            """ :type: TestFixture"""
            self.LOG.debug("Running fixture teardown: " + name)
            fix.teardown()

    def get_fixture(self, name):
        if name in self.fixtures:
            return self.fixtures[name]
        raise ObjectNotFoundException('No fixture defined in scenario: ' + name)

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
        if not issubclass(impl_class, TestScenario):
            raise ArgMismatchException('Class: ' + fqn + ' is not a subclass of TSM.TestCase')
        return impl_class
