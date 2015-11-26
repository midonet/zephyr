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

import traceback
import sys
import unittest
import logging
import datetime
import importlib
import inspect
import pkgutil
import os

from common.Exceptions import *
from common.LogManager import LogManager
from common.CLI import LinuxCLI

from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from VTM.VirtualTopologyManager import VirtualTopologyManager

from TSM.TestScenario import TestScenario
from TSM.TestCase import TestCase
from TSM.TestResult import TestResult

TSM_LOG_FILE_NAME = 'tsm-output.log'

DEFAULT_TEST_LOADER = {'unittest': unittest.defaultTestLoader }
DEFAULT_TEST_SUITE_TYPE = {'unittest': unittest.TestSuite }
DEFAULT_TEST_RUNNER = 'unittest'


class TestSystemManager(object):
    def __init__(self, ptm, vtm, log_manager=None, test_system=DEFAULT_TEST_RUNNER, debug=False):
        self.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        self.vtm = vtm
        """ :type: VirtualTopologyManager"""
        self.test_cases = {}
        """ :type: dict [TestCase, set[str]]"""
        self.result_map = {}
        """ :type: dict[TestScenario, TestResult]"""
        self.debug = debug
        """ :type: bool"""
        self.test_debug = False
        """ :type: bool"""
        self.log_manager = log_manager if log_manager is not None else LogManager('logs')
        """ :type: LogManager"""
        self.test_system = test_system
        """ :type: str"""
        self.test_loader = DEFAULT_TEST_LOADER[test_system]
        self.test_suite_type = DEFAULT_TEST_SUITE_TYPE[test_system]

        self.LOG = logging.getLogger('tsm-null-logger')
        """ :type: logging.Logger"""
        self.LOG.addHandler(logging.NullHandler())

        self.CONSOLE = logging.getLogger('tsm-null-console')
        """ :type: logging.Logger"""
        self.CONSOLE.addHandler(logging.NullHandler())

    def configure_logging(self, log_name='tsm-root', debug=False, log_file_name=TSM_LOG_FILE_NAME):
        self.debug = debug
        level = logging.INFO
        if debug is True:
            level = logging.DEBUG
            self.LOG = self.log_manager.add_tee_logger(file_name=log_file_name,
                                                       name=(log_name + '-debug'),
                                                       file_log_level=level,
                                                       stdout_log_level=level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(file_name=log_file_name,
                                                        name=log_name,
                                                        log_level=level)

        self.CONSOLE = self.log_manager.add_stdout_logger(name=log_name + '-console', log_level=level)

    def load_tests(self, test_case_list):
        """
        Load test cases from a list of strings
        :type test_case_list: list[str]
        """
        for i in test_case_list:
            self.LOG.debug("Adding test: " + str(i))
            self.add_test(i)

    def add_test(self, test):
        """
        Load a test from a fully-qualified name of a test package, module, class, or function.  The string
        can be one of the following:

        A) '(p.q.r...)' - A package name
        B) '(p.q.r...).mod' - A module in a (optionally named) package
        C) '((p.q.r...).mod.)cl' - A class in a (optionally named) module
        D) '((p.q.r...).mod.)cl.fn' - A function in the class

        The following should happen in each case:
        A) All classes in all modules in package p.q.r should be loaded separately.
        B) All classes in module mod (in package p.q.r) should be loaded separately.
        C) The class cl (in module mod (in package p.q.r)) should be loaded individually.
        D) The class cl (in module mod (in package p.q.r)) should be loaded and the test restricted to function fn.

        We will then store a) the class type itself and b) a list of test functions as strings (or None for all).

        :type test: str
        :return:
        """

        # For each step of the FQN hierarchy, try to (from specific to general):
        # a) load the class, then
        # b) load the module, then
        # c) find the package.
        # If a) succeeds, then look for function name.
        # If we get to the end, then try to load as specific an object as we've reached

        test_type_obj = None
        test_func_name = None

        fqn_split = test.split('.')

        current_module = None
        """ :type: module"""
        current_context = ''
        """ :type: str"""

        # Try to load as class(.function)
        if fqn_split[0] in globals():
            # This means the package/module aren't specified, so the current module must
            # already be loaded
            test_type_obj = globals()[fqn_split[0]]
            if len(fqn_split) > 1:
                test_func_name = fqn_split[1]

            # Now add the test class/functions to the test case list
            self.LOG.debug("Loading test case as class.func: " + str(test_type_obj.__name__) +
                           "/" + str(test_func_name))
            self.add_test_from_pkg_mod_cls_func('', test_type_obj, test_func_name)
            return

        # Not a global class/function, so try to load as package...module(.class(.function))
        #   As FQNs are set to be pkg1.pkg2.pkg3.module.class.function, the last three items
        #   can be expected to be in the format of mod[.cl[.fun]], with each successive field
        #   being optional.  You can't have a function without a class or a class without a
        #   module at this point (the class.func case was checked above), meaning we have
        #   either pkg...mod.class.func, pkg...mod.class, pkg...mod, or pkg...
        # So, loop here and work backwards.  First try the whole FQN as a module, then try
        #   one step back and load the FQN up to the last dot as a module (and the remainder
        #   as a class), then one more step back and FQN - 2 as a module with a class.func
        #   specifier.  Hence the "3" in this range (so we get FQN-0 dots, FQN-1 dot, and
        #   FQN-2 dots).
        for i in range(0, 3):
            if len(fqn_split) > i:
                try:
                    mod_package_part = fqn_split[:len(fqn_split)-i]
                    current_context = '.'.join(mod_package_part)
                    remainder_part = fqn_split[len(fqn_split)-i:]

                    # Get the base part of the FQN that we'll use as the package/module
                    current_module = importlib.import_module(current_context)
                    if len(remainder_part) > 0:
                        test_type_obj = getattr(current_module, remainder_part[0])
                        if len(remainder_part) > 1:
                            test_func_name = remainder_part[1]

                    break
                except ImportError:
                    # This module didn't load, so let's step one more step back and try again
                    current_module = None
                except AttributeError as e:
                    # Bad.  This means the module was imported fine, but the class wasn't in there!
                    raise ObjectNotFoundException('Malformed name: class: ' + fqn_split[len(fqn_split)-i:][0] +
                                                  ', not in module: ' + current_module.__name__)

        if current_module is None:
            # No module loaded, so this is not a valid FQN (should at least be a module/package in there!
            exc_str = 'No module can be loaded from the fully-qualified name: ' + test
            raise ObjectNotFoundException(exc_str)

        # Now current_package, current_module, and test_type_obj/test_func_name are all set:
        self.add_test_from_pkg_mod_cls_func(current_context, test_type_obj, test_func_name)

    def add_test_from_pkg_mod_cls_func(self, current_context, test_type_obj, test_func_name):
        """
        :parameter current_context: str The context (package/module) string of the current_module, if any
        :parameter current_module: module The desired package.module as a pre-loaded module, None if not specified
        :parameter test_type_obj: class The desired test case class as a python type, None if not specified
        :parameter test_func_name: str The desired function as a string, None if not specified

        Create a map of test_type_obj (as a python class type) to the list of functions to
          run on that test class.
        test_obj
           |
           V   func
        +-----+-----+--------+
        |     |  N  |  1,2   |
        |  N  |     +--------+
        |     | set | XXXXXX |
        +-----+-----+--------+
        |     |  N  |   3a   |
        | Set |     +--------+
        |     | set |   3b   |
        +-----+-----+--------+

        1:  Package (dir): Scan current_context dir and recursively add all packages and all
            Test*/test_* modules
        2:  Module (Py file): Scan for all classes in current_module (with package if present)
            and add each with None for func_list
        3a: Add class (with specific package/module if present) and None for func_list
        3a: Add class (with specific package/module if present) and append func to func_list
        """

        # First, check error conditions (XXXXXXX in chart above)
        if test_type_obj is None and test_func_name is not None:
            raise ArgMismatchException('Cannot specify function name without class name')

        if test_type_obj is not None:
            # Test type is specified (3a and 3b above)
            if test_type_obj not in self.test_cases:
                # Add a new test specification with test_func_name as a set (or None)
                self.LOG.debug("Adding test case to map: " + str(test_type_obj.__name__))
                self.test_cases[test_type_obj] = None
                if test_func_name is not None:
                    set_str = current_context + '.' + test_type_obj.__name__ + '.' + test_func_name
                    self.LOG.debug("Adding func to test case map: " + str(test_type_obj.__name__) + '=' +
                                   str(set_str))
                    self.test_cases[test_type_obj] = {set_str}
            else:
                # Alter an existing specification:  Only override if a more-general specification
                # is used.  This basically means if the func list is None, that's the most general,
                # otherwise, it is specifying an exact function, so we can just add them to the set
                # and any duplicates will be weeded out.
                if self.test_cases[test_type_obj] is not None:
                    set_str = current_context + '.' + test_type_obj.__name__ + '.' + test_func_name
                    self.LOG.debug("Adding func to existing test case map: " + str(test_type_obj.__name__) +
                                   '=' + str(set_str))
                    self.test_cases[test_type_obj].add(set_str)
        else:
            # No test object, so load all tests in module/package (1 and 2 above)
            mod = importlib.import_module(current_context)
            mod_file_name = mod.__file__.split('/')[-1]
            if (mod_file_name == '__init__.py' or mod_file_name == '__init__.pyc'):
                # If this __init__.py, it's a package, so load all modules underneath recursively
                for _, m, pkg in pkgutil.iter_modules(mod.__path__):
                    if pkg or m.startswith("test_") or m.startswith("Test"):
                        # This is a test_* or Test* module in this package, so load it
                        # Check that this module can be loaded
                        self.LOG.debug("Recursing with: " + str(current_context) + "." + str(m))
                        self.add_test_from_pkg_mod_cls_func(current_context + "." + m, None, None)
            else:
                # If this is a real python file, it's a module (i.e. .Cassandra or .pyc file), so load it directly
                try:
                    for test_name, test in \
                            inspect.getmembers(mod,
                                               predicate=lambda m: inspect.isclass(m) and m.__module__ == mod.__name__):
                        if test_name != 'TestCase' and \
                                inspect.isclass(test) and issubclass(test, TestCase):
                            self.LOG.debug("Recursing with: " + str(current_context) + " and test: " + str(test))
                            self.add_test_from_pkg_mod_cls_func(current_context, test, None)
                except ImportError as e:
                    # Nope, just kidding, skip it.
                    self.LOG.debug("Couldn't load test module: " + current_context + " because: " + str(e))

    def set_test_debug(self, debug_flag=True):
        self.test_debug=debug_flag

    def run_all_tests(self, scenario_filter=None):
        """
        Clear previous results and run all tests and return the list of TestResults from the run
        :type scenario_filter: list[callable]
        :return: dict [TestScenario, TestResult]
        """
        self.result_map.clear()
        tests_by_scenario_map = {}

        # Rearrange list based on scenarios
        for test, func_set in self.test_cases.iteritems():
            self.LOG.debug('Creating scenario map for test: ' + test._get_name())
            for scen in test.supported_scenarios():
                if issubclass(test, TestCase) and (scenario_filter is None or scen in scenario_filter):
                    if scen not in tests_by_scenario_map:
                        tests_by_scenario_map[scen] = []
                    self.LOG.debug('Adding test: ' + test._get_name() + ' to scenario [' + scen.__name__ + ']')
                    tests_by_scenario_map[scen].append((test, func_set))

        for scen, test_list in tests_by_scenario_map.iteritems():
            result = self.run_scenario(scen, test_list)
            self.result_map[scen] = result

        return self.result_map

    def test_suite_to_flat_list(self, test_suite):
        """
        Flattens the given TestSuite so that only TestCases are inside (no nested TestSuites)
        :type test_suite: TestSuite
        :return: list[TestCase]
        """
        ret_list = []
        for t in test_suite:
            if isinstance(t, self.test_suite_type):
                ret_list += self.test_suite_to_flat_list(t)
            elif isinstance(t, TestCase):
                ret_list.append(t)
            else:
                raise ArgMismatchException('Unknown object type in Suite: ' + t.__type__.__name__)
        return ret_list

    def run_scenario(self, scenario, test_list):
        """
        Run a given test with all scenarios the test supports, unless a filter list is given,
        in which case, only run the test with listed scenarios if the test case supports it.
        :type scenario: callable
        :type test_list: list[(TestCase, set[str]|None)]
        :return: TestResult
        """

        if not issubclass(scenario, TestScenario):
            raise ArgMismatchException('Scenario class is not a subclass of TSM.TestScenario: ' + scenario.__name__)

        scenario_result = TestResult(scenario)

        self.LOG.debug('Running scenario [' + scenario.__name__ + '] with tests: ' +
                       str([t[0].__name__ + ' (' + (', '.join(t[1]) if t[1] else 'all') + ')' for t in test_list]))

        scenario_obj = scenario(self.ptm, self.vtm)
        """ :type scenario_obj: TestScenario"""
        scenario_name = scenario_obj.__class__.__name__
        log_file_name = scenario_name + ".log"

        scenario_obj.configure_logging(log_name=scenario_name, debug=self.debug, log_file_name=log_file_name)
        if self.test_system == 'unittest':
            # Prepare suite with specific functions (or whole class if func_set not specified)
            suite = unittest.TestSuite()
            """ :type suite: unittest.TestSuite"""

        # Prepare all of the test classes in this scenario before run.  This will set up the
        # entire class type with certain class-globals so that any instances of the class
        # will have its scenario and logger set.
        for test_class, func_set in test_list:
            # Just check that the current scenario is supported by this test class.  It should be
            # if the normal "run_all_tests" function was run, but if this fn is run directly,
            # we will need to check here as well.
            if scenario not in test_class.supported_scenarios():
                continue

            test_class_name = test_class._get_name()
            scenario_obj.LOG.debug('TSM: Preparing scenario: ' + scenario_name)
            if self.debug:
                testcase_log = self.log_manager.add_tee_logger(name=test_class._get_name().split('.')[-1] + '-debug',
                                                               file_name=log_file_name,
                                                               file_log_level=logging.DEBUG,
                                                               stdout_log_level=logging.DEBUG)
                testcase_log.info('Starting debug logs')
            else:
                testcase_log = self.log_manager.add_file_logger(name=test_class._get_name().split('.')[-1],
                                                                file_name=log_file_name,
                                                                log_level=logging.INFO)

            testcase_log.debug('TSM: Preparing test class: ' + test_class._get_name())
            test_class._prepare_class(scenario_obj, testcase_log)

            test_loader = DEFAULT_TEST_LOADER[self.test_system]
            if func_set is None:
                suite.addTest(test_loader.loadTestsFromTestCase(test_class))
            else:
                suite.addTest(test_loader.loadTestsFromNames(func_set))

        # Flatten the tests
        running_suite = unittest.TestSuite(self.test_suite_to_flat_list(suite))

        # Run the test by setting up the scenario, then executing the case, and
        # finally cleaning up the scenario
        try:
            try:
                scenario_obj.LOG.debug('Setting up scenario [' + scenario_name + ']')
                scenario_obj.setup()
                scenario_obj.fixture_setup()
            except Exception as e:
                self.LOG.fatal('Fatal error starting up scenario: ' + scenario_name)
                self.LOG.fatal('Traceback: ')
                self.LOG.fatal(traceback.format_tb(sys.exc_traceback))
                dummy_tc = TestCase()
                dummy_tc.start_time = datetime.datetime.utcnow()
                dummy_tc.stop_time = datetime.datetime.utcnow()
                dummy_tc.run_time = datetime.timedelta()
                dummy_tc.current_scenario = scenario_obj
                dummy_tc.failureException = e
                scenario_result.addError(dummy_tc, sys.exc_info())
                return scenario_result

            scenario_result.start_time = datetime.datetime.utcnow()
            scenario_obj.LOG.debug('Starting scenario [' + scenario_name + '] at timestamp[' +
                               str(scenario_result.start_time) + ']')
            if self.test_system == 'unittest':
                running_suite.run(scenario_result, debug=self.test_debug)
            scenario_result.stop_time = datetime.datetime.utcnow()
            scenario_obj.LOG.debug('Finished scenario [' + scenario_name + '] at timestamp[' +
                               str(scenario_result.stop_time) + ']')
            scenario_result.run_time = (scenario_result.stop_time - scenario_result.start_time)
        finally:
            scenario_obj.LOG.debug('Tearing down scenario [' + scenario_name + ']')
            scenario_obj.teardown()
            scenario_obj.fixture_teardown()

        return scenario_result

    def create_results(self, results_dir='./results', leeway=5):
        self.LOG.debug("Creating test_results")
        cli = LinuxCLI(priv=False)
        cli.rm(results_dir)
        for scen, res in self.result_map.iteritems():
            self.LOG.debug("Creating test_results for scenario: " + scen.__name__)
            results_out_dir = results_dir + '/' + scen.__name__

            cli.write_to_file(wfile=results_out_dir + '/results.xml',
                              data=res.to_junit_xml())
            self.log_manager.collate_logs(results_out_dir + '/full-logs')

            for tc in res.all_tests():
                if isinstance(tc, TestCase):
                    tcname = tc.id().split('.')[-1]
                    self.LOG.debug("Creating test_results for " + tcname)
                    cli.mkdir(results_out_dir + '/' + tcname)
                    self.log_manager.slice_log_files_by_time(results_out_dir + '/' + tcname,
                                                             start_time=tc.start_time if tc.start_time is not None else '0.0',
                                                             stop_time=tc.stop_time if tc.start_time is not None else '0.0',
                                                             leeway=leeway,
                                                             collated_only=True)

