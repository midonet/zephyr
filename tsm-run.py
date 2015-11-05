#!/usr/bin/env python
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import getopt
import traceback
import datetime
import logging

from common.Exceptions import *
from common.CLI import LinuxCLI
from common.LogManager import LogManager


from PTM.PhysicalTopologyManager import PhysicalTopologyManager, CONTROL_CMD_NAME

from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.MNAPI import create_midonet_client
from VTM.NeutronAPI import create_neutron_client

from TSM.TestSystemManager import TestSystemManager
from TSM.TestScenario import TestScenario
from TSM.TestCase import TestCase


def usage(exceptObj):
    print 'Usage: tsm-run.py -t <tests> [-s <scenarios>] [-p <file>]'
    print '                             [-c <neutron|midonet> --client-args="<arg=value,...>"]'
    print '                             [extra_options]'
    print ''
    print '   Options:'
    print '     -t, --tests <tests>          List of fully-qualified names of tests to run, separated by '
    print '                                  commas with no spaces.'
    print '     -s, --scenarios <scenarios>  List of fully-qualified names of scenarios to use as a filter,'
    print '                                  allowing the given tests to execute under the listed scenarios.'
    print '                                  By default, each test will run all of its supported scenarios.'
    print '     -c, --client <client>        OpenStack Network client to use.  Currently can be either '
    print '                                  "neutron" (default) or "midonet".'
    print '     --client-args <args>         List of arguments to give the selected client.  These should be'
    print '                                  key=value pairs, separated by commas, with no spaces.'
    print '   Extra Options:'
    print '     -l, --log-dir <dir>          Log file directory (default: /tmp/zephyr/results)'
    print '     -r, --results-dir <dir>      Results file directory (default: /tmp/zephyr/logs) Timestamp'
    print '                                  will be appended to prevent overwriting results.'

    if exceptObj is not None:
        raise exceptObj

try:
    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hvdt:s:c:p:l:r:',
                                        ['help', 'tests=', 'scenarios=', 'client=', 'client-args=', 'ptm=',
                                         'log-dir=', 'debug', 'results-dir=', 'debug-test'])

    # Defaults
    client_impl_type = 'neutron'
    client_args = {}
    tests = ''
    scenario_filter_list = ''
    ptm_config_file = ''
    debug = False
    test_debug = False
    log_dir = '/tmp/zephyr/logs'
    results_dir = '/tmp/zephyr/results'

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-t', '--tests'):
            if value == '':
                usage(ArgMismatchException('Tests should be given as a comma-delimited list with no spaces'))
            tests = value.split(',')
        elif arg in ('-s', '--scenarios'):
            if value == '':
                usage(ArgMismatchException('Scenarios should be given as a comma-delimited list with no spaces'))
            scenario_filter_list = value.split(',')
        elif arg in ('-c', '--client'):
            client_impl_type = value
            pass
        elif arg in ('-l', '--log-dir'):
            log_dir = value
            pass
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in ('--debug-test'):
            test_debug = True
        elif arg in ('-r', '--results-dir'):
            results_dir = value
            pass
        elif arg == '--client-args':
            for kv in value.split(','):
                if kv == '':
                    usage(ArgMismatchException('Client args should be key=value pairs, with one "=", '
                                               'separated by "," and no spaces.'))

                p = kv.split('=')
                if len(p) != 2:
                    usage(ArgMismatchException('Client args should be key=value pairs, with one "=", '
                                               'separated by "," and no spaces.'))
                client_args[p[0]] = p[1]
            pass
        else:
            raise ArgMismatchException('Invalid argument' + arg)

    if len(tests) == 0:
        usage(ArgMismatchException('Must specify at least one test with the -t or --tests option'))

    root_dir = LinuxCLI().cmd('pwd').stdout.strip()
    print 'Setting root dir to: ' + root_dir

    client_impl = None
    if client_impl_type == 'neutron':
        client_impl = create_neutron_client(**client_args)
    elif client_impl_type == 'midonet':
        client_impl = create_midonet_client(**client_args)
    else:
        raise ArgMismatchException('Invalid client API implementation:' + client_impl_type)

    print 'Setting up log manager with debug=' + str(debug)
    log_manager = LogManager(root_dir=log_dir)
    console_log = log_manager.add_stdout_logger(name='tsm-run-console',
                                                log_level=logging.DEBUG if debug is True else logging.INFO)
    log_manager.rollover_logs_fresh(file_filter='*.log')

    console_log.debug('Setting up PTM')
    ptm = PhysicalTopologyManager(root_dir=root_dir, log_manager=log_manager)
    ptm.configure_logging(debug=debug)

    console_log.debug('Setting up VTM')
    vtm = VirtualTopologyManager(physical_topology_manager=ptm, client_api_impl=client_impl, log_manager=log_manager)

    console_log.debug('Setting up TSM')
    tsm = TestSystemManager(ptm, vtm, log_manager=log_manager)
    tsm.configure_logging(debug=debug)

    if test_debug:
        tsm.set_test_debug()

    scenario_filters = [TestScenario.get_class(s) for s in scenario_filter_list] \
        if len(scenario_filter_list) != 0 else None

    console_log.debug('Test Case Classes = ' + str(tests))

    # Run test cases, possibly filtered on scenarios
    tsm.load_tests(tests)

    console_log.debug('Running all tests with scenario filter: ' + str(scenario_filters))

    try:
        results = tsm.run_all_tests(scenario_filters)

        for s, tr in results.iteritems():
            print '========================================'
            print 'Scenario [' + s.__name__ + ']'
            print 'Passed [{0}/{1}]'.format(len(results[s].successes), results[s].testsRun)
            print 'Failed [{0}/{1}]'.format(len(results[s].failures), results[s].testsRun)
            print 'Error [{0}/{1}]'.format(len(results[s].errors), results[s].testsRun)
            print ''
            for tc, err in results[s].failures:
                print '------------------------------'
                print 'Test Case FAILED: [' + tc._get_name() + ']'
                print 'Failure Message:'
                print err

            for tc, err in results[s].errors:
                if isinstance(tc, TestCase):
                    print '------------------------------'
                    print 'Test Case ERROR: [' + tc._get_name() + ']'
                    print 'Error Message:'
                    print err
                else:
                    print '------------------------------'
                    print 'Test Framework ERROR'
                    print 'Error Message:'
                    print err

    finally:
        rdir = results_dir + '/' + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        tsm.create_results(results_dir=rdir, leeway=3)

except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print 'Argument mismatch: ' + str(a)
    exit(2)
except ObjectNotFoundException as e:
    print 'Object not found: ' + str(e)
    exit(2)
except SubprocessFailedException as e:
    print 'Subprocess failed to execute: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print 'Unknown exception: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
