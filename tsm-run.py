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

import os
import sys
import getopt
import traceback
import datetime
import logging

from common.Exceptions import *
from common.CLI import LinuxCLI
from common.LogManager import LogManager
from common.Utils import get_class_from_fqn
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.MNAPI import create_midonet_client
from VTM.NeutronAPI import create_neutron_client
from TSM.TestSystemManager import TestSystemManager
from TSM.TestCase import TestCase


def usage(exceptObj):
    print('Usage: tsm-run.py -t <tests> [-t <topology>] [-n <name>] [-p <file>] [-d] ')
    print('                             [-c <neutron|midonet> --client-args="<arg=value,...>"]')
    print('                             [-p <ptm_class>] [extra_options]')
    print('')
    print('   Test Execution Options:')
    print('     -t, --tests <tests>          List of fully-qualified names of tests to run, separated by ')
    print('                                  commas with no spaces.')
    print('     -n, --name <name>            Name this test run (timestamp by default).')
    print('   Client API Options:')
    print('     -c, --client <client>        OpenStack Network client to use.  Currently can be either ')
    print('                                  "neutron" (default) or "midonet".')
    print('     -a, --client-auth <auth>     Authentication scheme to use for Openstack authentication. Can be')
    print('                                  "noauth" or "keystone" ("noauth" is default).')
    print('                                  "neutron" (default) or "midonet".')
    print('     --client-args <args>         List of arguments to give the selected client.  These should be')
    print('                                  key=value pairs, separated by commas, with no spaces.')
    print('   Physical Topology Management Options:')
    print('     -p, --ptm <ptm-class>        Use the specified PTM implementation class')
    print('                                  (ConfiguredHostPTMImpl is the default).')
    print('   ConfiguredHostPTMImpl Specific Options:')
    print('     -o, --topology <topo>        State which physical topologys to configure and run.  Topologies are')
    print('                                  defined in config/physical_topologies.  By default, tests will run ')
    print('                                  against a 2NSDB + 3Compute + 2Edge topology. Only one topology can ')
    print('                                  be run per execution of this command.')
    print('   Debug Options:')
    print('     -d, --debug                  Turn on DEBUG logging (and split log output to stdout).')
    print('   Output File Options:')
    print('     -l, --log-dir <dir>          Log file directory (default: /tmp/zephyr/results)')
    print('     -r, --results-dir <dir>      Results file directory (default: /tmp/zephyr/logs) Timestamp')
    print('                                  will be appended to prevent overwriting results.')

    if exceptObj is not None:
        raise exceptObj

try:
    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hvdt:n:o:c:p:l:r:a:',
                                        ['help', 'tests=', 'name=', 'topologies=',
                                         'client=', 'client-auth=', 'client-args=',
                                         'ptm=', 'log-dir=', 'debug', 'results-dir=', 'debug-test'])

    # Defaults
    client_impl_type = 'neutron'
    client_auth_type = 'noauth'
    client_args = {}
    tests = ''
    ptm_config_file = ''
    debug = False
    test_debug = False
    log_dir = '/tmp/zephyr/logs'
    results_dir = '/tmp/zephyr/results'
    ptm_impl_type = 'PTM.impl.ConfiguredHostPTMImpl'
    topology = 'config/physical_topologies/2z-3c-2edge.json'
    name = datetime.datetime.utcnow().strftime('%Y_%m_%d_%H-%M-%S')

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-t', '--tests'):
            if value == '':
                usage(ArgMismatchException('Tests should be given as a comma-delimited list with no spaces'))
            tests = value.split(',')
        elif arg in ('-n', '--name'):
            name = value
        elif arg in ('-o', '--topologies'):
            topology = value
        elif arg in ('-c', '--client'):
            client_impl_type = value
        elif arg in ('-a', '--client-auth'):
            client_auth_type = value
        elif arg in ('-p', '--ptm'):
            ptm_impl_type = value
        elif arg in ('-l', '--log-dir'):
            log_dir = value
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in ('--debug-test'):
            test_debug = True
        elif arg in ('-r', '--results-dir'):
            results_dir = value
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
        else:
            raise ArgMismatchException('Invalid argument' + arg)

    if len(tests) == 0:
        usage(ArgMismatchException('Must specify at least one test with the -t or --tests option'))

    root_dir = LinuxCLI().cmd('pwd').stdout.strip()
    print('Setting root dir to: ' + root_dir)

    client_impl = None
    base_client_args = dict()
    if client_impl_type == 'neutron':
        if client_auth_type == 'keystone':
            base_client_args = {'auth_strategy': 'keystone',
                                'auth_url': os.environ.get('OS_ATUH_URL', 'http://localhost:5000/v2.0'),
                                'username': os.environ.get('OS_USERNAME', 'admin'),
                                'password': os.environ.get('OS_PASSWORD', 'cat'),
                                'tenant_name': os.environ.get('OS_TENANT_NAME', 'admin')}
        base_client_args.update(client_args)
        client_impl = create_neutron_client(**base_client_args)
    elif client_impl_type == 'midonet':
        client_impl = create_midonet_client(**client_args)
    else:
        raise ArgMismatchException('Invalid client API implementation:' + client_impl_type)

    print('Setting up log manager with debug=' + str(debug))
    log_manager = LogManager(root_dir=log_dir)
    console_log = log_manager.add_stdout_logger(name='tsm-run-console',
                                                log_level=logging.DEBUG if debug is True else logging.INFO)
    log_manager.rollover_logs_fresh(file_filter='*.log')

    console_log.debug('Setting up PTM from impl: ' + ptm_impl_type)
    ptm_impl = get_class_from_fqn(ptm_impl_type)(root_dir=root_dir, log_manager=log_manager)
    ptm_impl.configure_logging(debug=debug)
    ptm = PhysicalTopologyManager(ptm_impl)

    console_log.debug('Setting up VTM')
    vtm = VirtualTopologyManager(physical_topology_manager=ptm, client_api_impl=client_impl, log_manager=log_manager)
    vtm.configure_logging(debug=debug)

    console_log.debug('Setting up TSM')
    tsm = TestSystemManager(ptm, vtm, log_manager=log_manager)
    tsm.configure_logging(debug=debug)

    if test_debug:
        tsm.set_test_debug()

    console_log.debug('Test Case Classes = ' + str(tests))

    # Run test cases, possibly filtered on scenarios
    tsm.load_tests(tests)

    console_log.debug('Running all tests with topology: ' + str(topology))

    try:
        results = tsm.run_all_tests(name, topology)

        for suite, result in tsm.result_map.iteritems():
            print('========================================')
            print('Suite [' + suite + ']')
            print('Passed [{0}/{1}]'.format(len(result.successes), result.testsRun))
            print('Expected Failures [{0}/{1}]'.format(len(result.expectedFailures), result.testsRun))
            print('Failed [{0}/{1}]'.format(len(result.failures), result.testsRun))
            print('Error [{0}/{1}]'.format(len(result.errors), result.testsRun))
            print('')
            for tc, err in result.failures:
                print('------------------------------')
                print('Test Case FAILED: [' + tc._get_name() + ']')
                print('Failure Message:')
                print(err)

            for tc, err in result.expectedFailures:
                print('------------------------------')
                print('Test Case passed with EXPECTED FAILURE: [' + tc._get_name() +
                      '], see issue(s) [' + ','.join(tc.expected_failure_issue_ids) + ']')
                print('Failure Message:')
                print(err)

            for tc, err in result.errors:
                if isinstance(tc, TestCase):
                    print('------------------------------')
                    print('Test Case ERROR: [' + tc._get_name() + ']')
                    print('Error Message:')
                    print(err)
                else:
                    print('------------------------------')
                    print('Test Framework ERROR')
                    print('Error Message:')
                    print(err)

            for tc, err in result.skipped:
                print('------------------------------')
                print('Test Case SKIPPED: [' + tc._get_name() + ']')
                print('Reason:')
                print(err)

    finally:
        rdir = results_dir + '/' + name
        tsm.create_results(results_dir=rdir, leeway=3)

except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print('Argument mismatch: ' + str(a))
    exit(2)
except ObjectNotFoundException as e:
    print('Object not found: ' + str(e))
    exit(2)
except SubprocessFailedException as e:
    print('Subprocess failed to execute: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print('Unknown exception: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
