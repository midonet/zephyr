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
import datetime

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
        self.log_manager = log_manager if log_manager is not None else LogManager('logs')
        """ :type: LogManager"""

        self.LOG = logging.getLogger('tsm-null-logger')
        """ :type: logging.Logger"""
        self.LOG.addHandler(logging.NullHandler())

        self.CONSOLE = logging.getLogger('tsm-null-console')
        """ :type: logging.Logger"""
        self.CONSOLE.addHandler(logging.NullHandler())

    def configure_logging(self, log_name='tsm-root', log_file_name=TSM_LOG_FILE_NAME, debug=False):

        level = logging.INFO
        if debug:
            level = logging.DEBUG
            self.LOG = self.log_manager.add_tee_logger(file_name=log_file_name,
                                                        name=(log_name + '-debug'),
                                                        file_log_level=level,
                                                        stdout_log_level=level)
        else:
            self.LOG = self.log_manager.add_file_logger(file_name=log_file_name,
                                                        name=(log_name + '-debug'),
                                                        log_level=level)

        self.CONSOLE = self.log_manager.add_stdout_logger(name=log_name + '-console', log_level=level)

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
        :return: dict [TestScenario, TestResult]
        """
        self.result_map.clear()
        tests_by_scenario_map = {}

        # Rearrange list based on scenarios
        for test in self.test_cases.itervalues():
            self.LOG.debug('Creating scenario map for test: ' + test._get_name())
            for scen in test.supported_scenarios():
                if scenario_filter is None or scen in scenario_filter:
                    self.LOG.debug('Adding scenario [' + scen.__name__ + '] to test: ' + test._get_name())
                    if scen not in tests_by_scenario_map:
                        tests_by_scenario_map[scen] = []
                    tests_by_scenario_map[scen].append(test)

        for scen, test_list in tests_by_scenario_map.iteritems():
            result = self.run_scenario(scen, test_list)
            self.result_map[scen] = result

        return self.result_map

    def run_scenario(self, scenario, test_list):
        """
        Run a given test with all scenarios the test supports, unless a filter list is given,
        in which case, only run the test with listed scenarios if the test case supports it.
        :type scenario: callable
        :type test_list: list[TestCase]
        :return: TestResult
        """

        if not issubclass(scenario, TestScenario):
            raise ArgMismatchException('Scenario class is not a subclass of TSM.TestScenario: ' + scenario.__name__)

        scenario_result = TestResult(scenario)

        for test_class in test_list:
            if not issubclass(test_class, TestCase):
                raise ArgMismatchException('Test case class is not a subclass of TSM.TestCase: ' + test_class.__name__)

            if scenario in test_class.supported_scenarios():
                scenario_obj = scenario(self.ptm, self.vtm)
                """ :type scenario_obj: TestScenario"""

                log_file_name = test_class._get_name() + "-" + scenario_obj.__class__.__name__ + ".log"
                tsm_log = self.log_manager.add_file_logger(name=scenario_obj.__class__.__name__,
                                                            file_name=log_file_name,
                                                            log_level=logging.DEBUG)

                tsm_log.info('TSM: Preparing test class: ' + test_class._get_name())
                test_class._prepare_class(scenario_obj, tsm_log)

                test_loader = unittest.defaultTestLoader
                suite = test_loader.loadTestsFromTestCase(test_class)
                """ :type suite: unittest.TestSuite"""

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
                    scenario_result.start_time = datetime.datetime.utcnow()
                    suite.run(scenario_result, debug=self.debug)
                    scenario_result.stop_time = datetime.datetime.utcnow()
                    scenario_result.run_time = (scenario_result.stop_time - scenario_result.start_time)
                finally:
                    scenario_obj.teardown()

        return scenario_result

    def create_results(self, results_dir='./results', leeway=5):
        cli = LinuxCLI(priv=False)
        cli.rm(results_dir)
        for scen, res in self.result_map.iteritems():
            log_out_dir = results_dir + '/' + scen.__name__

            cli.write_to_file(wfile=log_out_dir + '/results.xml',
                              data=res.to_junit_xml())
            self.log_manager.collate_logs(log_out_dir + '/full-logs')

            for tc in res.all_tests():
                tcname = tc.id().split('.')[-1]
                cli.mkdir(log_out_dir + '/' + tcname)
                self.log_manager.slice_log_files_by_time(log_out_dir + '/' + tcname,
                                                         start_time=tc.start_time,
                                                         stop_time=tc.stop_time,
                                                         leeway=leeway,
                                                         collated_only=True)

