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
import inspect
import unittest
import logging

from common.Exceptions import *
from common.LogManager import LogManager
from common.CLI import LinuxCLI

from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from VTM.VirtualTopologyManager import VirtualTopologyManager

from TSM.TestScenario import TestScenario
from TSM.TestCase import TestCase
from TSM.TestResult import TestResult

TSM_LOG_FILE_NAME = 'tsm-output.log'

class TestSystemManager(object):
    def __init__(self, ptm, vtm, log_manager=None, debug=False):
        self.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        self.vtm = vtm
        """ :type: VirtualTopologyManager"""
        self.test_cases = {}
        """ :type: dict [str, TestCase]"""
        self.result_map = {}
        """ :type: dict[TestScenario, TestResult]"""
        self.debug = debug
        """ :type: bool"""
        self.log_manager = log_manager
        """ :type: LogManager"""
        self.LOG = logging.getLogger()
        """ :type: logging.Logger"""
        self.CONSOLE = logging.getLogger()
        """ :type: logging.Logger"""

    def configure_logging(self, log_name='tsm-root', log_file_name=TSM_LOG_FILE_NAME):

        self.LOG = self.log_manager.add_file_logger(file_name=log_file_name,
                                                    name=(log_name + '-debug'),
                                                    log_level=logging.DEBUG)

        self.CONSOLE = self.log_manager.add_stdout_logger(name=log_name + '-console', log_level=logging.INFO)

    def load_tests(self, test_case_list):
        """
        Load test cases from a list of strings
        :type test_case_list: list[str]
        """
        for i in test_case_list:
            self.add_test(i)

    def add_test(self, test):
        self.test_cases[test._get_name()] = test

    def run_all_tests(self, scenario_filter=None):
        """
        Clear previous results and run all tests and return the list of TestResults from the run
        :type scenario_filter: list[callable]
        :return: list [TestResult]
        """
        self.result_map.clear()
        for test in self.test_cases.itervalues():
            self.run_case(test, scenario_filter)
        return self.result_map

    def run_case(self, test_class, scenario_filter=None):
        """
        Run a given test with all scenarios the test supports, unless a filter list is given,
        in which case, only run the test with listed scenarios if the test case supports it.
        :type test_class: TestCase
        :type scenario_filter: list[callable]
        :return: list [TestResult]
        """
        if not issubclass(test_class, TestCase):
            raise ArgMismatchException('Test case class is not a subclass of TSM.TestCase: ' + test_class.__name__)

        test_loader = unittest.defaultTestLoader

        for scenario in scenario_filter if scenario_filter is not None and len(scenario_filter) \
                else test_class.supported_scenarios():
            if scenario in test_class.supported_scenarios():
                if scenario not in self.result_map:
                    self.result_map[scenario] = TestResult(scenario)
                scenario_result = self.result_map[scenario]

                scenario_obj = scenario(self.ptm, self.vtm)
                """ :type suite: TestScenario"""

                suite = test_loader.loadTestsFromTestCase(test_class)
                """ :type suite: logging.TestSuite"""

                log_file_name = test_class._get_name() + "-" + scenario_obj.__class__.__name__ + ".log"
                tsm_log = self.log_manager.add_file_logger(name=scenario_obj.__class__.__name__,
                                                            file_name=log_file_name,
                                                            log_level=logging.DEBUG)

                tsm_log.info('TSM: Preparing test class: ' + test_class._get_name())
                test_class._prepare_class(scenario_obj, tsm_log)

                for tc in suite:
                    test_log = self.log_manager.add_file_logger(name=tc.id().split('.')[-1],
                                                                file_name=log_file_name,
                                                                log_level=logging.DEBUG)
                    test_log.debug('TSM: Setting logger on test: ' + tc.id())
                    tc.set_logger(test_log)

                # Run the test by setting up the scenario, then executing the case, and
                # finally cleaning up the scenario
                try:
                    scenario_obj.setup()
                    suite.run(scenario_result, debug=self.debug)
                finally:
                    scenario_obj.teardown()

        return self.result_map

    def make_results_file(self, results_dir='./results'):
        for scen, res in self.result_map.iteritems():
            LinuxCLI(priv=False).write_to_file(wfile=results_dir + '/' + scen.__name__ + '-results.xml',
                                               data=res.to_junit_xml())