#!/usr/bin/env python
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import getopt
import traceback

from common.Exceptions import *
from common.CLI import LinuxCLI
from common.LogManager import LogManager

from CBT.EnvSetup import EnvSetup

from PTM.PhysicalTopologyManager import PhysicalTopologyManager, CONTROL_CMD_NAME

from VTM.VirtualTopologyManager import VirtualTopologyManager, create_neutron_client
from VTM.MNAPI import create_midonet_client

from TSM.TestSystemManager import TestSystemManager
from TSM.TestScenario import TestScenario
from TSM.TestCase import TestCase


def usage(exceptObj):
    print 'Usage: tsm-run.py -t <tests> [-s <scenarios>] [-p <file>]'
    print '                             [-c <neutron|midonet> --client-args="<arg=value,...>"]'
    print ''
    print '   Options:'
    print '     -t, --tests <tests>          List of fully-qualified names of tests to run, separated by '
    print '                                  commas with no spaces.'
    print '     -s, --scenarios <scenarios>  List of fully-qualified names of scenarios to use as a filter,'
    print '                                  allowing the given tests to execute under the listed scenarios.'
    print '                                  By default, each test will run all of its supported scenarios.'
    print '     -c, --client <client>        OpenStack Network client to use.  Currently can be either '
    print "                                  'neutron' (default) or 'midonet'."
    print '     --client-args <args>         List of arguments to give the selected client.  These should be'
    print '                                  key=value pairs, separated by commas, with no spaces.'

    if exceptObj is not None:
        raise exceptObj

try:
    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hvdt:s:c:p:',
                                        ['help', 'tests=', 'scenarios=', 'client=', 'client-args=', 'ptm='])

    # Defaults
    client_impl_type = 'neutron'
    client_args = {}
    tests = ''
    scenario_filter_list = ''
    ptm_config_file = ''

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

    root_dir = LinuxCLI().cmd('pwd').strip()
    print "Setting root dir to: " + root_dir

    client_impl = None
    if client_impl_type == 'neutron':
        client_impl = create_neutron_client(**client_args)
    elif client_impl_type == 'midonet':
        client_impl = create_midonet_client(**client_args)
    else:
        raise ArgMismatchException('Invalid client API implementation:' + client_impl_type)

    log_manager = LogManager()

    ptm = PhysicalTopologyManager(root_dir=root_dir, log_manager=log_manager)
    vtm = VirtualTopologyManager(physical_topology_manager=ptm, client_api_impl=client_impl, log_manager=log_manager)
    tsm = TestSystemManager(ptm, vtm, log_manager=log_manager)

    scenario_filters = [TestScenario.get_class(s) for s in scenario_filter_list]
    test_cases = map(TestCase.get_class, tests)

    print test_cases
    print tests

    # Run test cases, possibly filtered on scenarios
    tsm.load_tests(test_cases)

    results = tsm.run_all_tests(scenario_filters)

    for s in results.iterkeys():
        print "========================================"
        print "Scenario [" + s.__name__ + "]"
        print "Passed [{0}/{1}]".format(len(results[s].successes), results[s].testsRun)
        print "Failed [{0}/{1}]".format(len(results[s].failures), results[s].testsRun)
        print "Error [{0}/{1}]".format(len(results[s].errors), results[s].testsRun)
        print ""
        for tc, err in results[s].failures:
            print "------------------------------"
            print "Test Case FAILED: [" + tc._get_name() + "]"
            print "Failure Message:"
            print err

        for tc, err in results[s].errors:
            if isinstance(tc, TestCase):
                print "------------------------------"
                print "Test Case ERROR: [" + tc._get_name() + "]"
                print "Error Message:"
                print err
            else:
                print "------------------------------"
                print "Test Framework ERROR"
                print "Error Message:"
                print err



except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print 'Argument mismatch: ' + str(a)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except ObjectNotFoundException as e:
    print 'Object not found: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except SubprocessFailedException as e:
    print 'Subprocess failed to execute: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print 'Unknown exception: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
