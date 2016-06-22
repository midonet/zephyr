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

import datetime
import getopt
import logging
import os
import sys
import traceback

from zephyr.common.exceptions import ArgMismatchException
from zephyr.common.exceptions import ExitCleanException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.exceptions import SubprocessFailedException
from zephyr.common.exceptions import TestException
from zephyr.common.log_manager import LogManager
from zephyr.common import zephyr_constants as z_con
from zephyr.tsm.test_case import TestCase
from zephyr.tsm.test_system_manager import TestSystemManager
from zephyr.vtm.neutron_api import create_neutron_client
from zephyr.vtm.virtual_topology_manager import VirtualTopologyManager


def usage(except_obj):
    print('Usage: tsm-run.py -t <tests> ')
    print('                  [-u <underlay_config>] [-n <name>] [-d]')
    print('                  [extra_options]')
    print('')
    print('   Test Execution Options:')
    print('     -t, --tests <tests>')
    print('         List of fully-qualified names of tests to run,')
    print('         separated by commas with no spaces.')
    print('     -n, --name <name>')
    print('         Name this test run (timestamp by default).')
    print('   Underlay Options:')
    print('     -u, --underlay_config <config>')
    print('         Load the underlay from the given config file. ')
    print('         ("' + z_con.DEFAULT_UNDERLAY_CONFIG + '" by default)')
    print('   Client API Options:')
    print('     -c, --client <client>')
    print('         OpenStack Network client to use.  Currently can be')
    print('         either "neutron" (default) or "midonet".')
    print('     -a, --client-auth <auth>')
    print('         Authentication scheme to use for Openstack ')
    print('         authentication. Can be"noauth" or "keystone" ("noauth"')
    print('         is default).')
    print('     --client-args <args>')
    print('         List of arguments to give the selected client.  These')
    print('         should be key=value pairs, separated by commas, with no')
    print('         spaces.')
    print('   Debug Options:')
    print('     -d, --debug')
    print('         Turn on DEBUG logging (and split log output to stdout).')
    print('   Output File Options:')
    print('     -l, --log-dir <dir>')
    print('         Log file directory (default: /tmp/zephyr/results)')
    print('     -r, --results-dir <dir>')
    print('         Results file directory (default: /tmp/zephyr/logs).')
    print('         Timestamp will be appended to prevent overwriting')
    print('         results.')

    if except_obj is not None:
        raise except_obj

try:
    arg_map, extra_args = getopt.getopt(
        sys.argv[1:],
        (
            'h'
            'v'
            'd'
            't:'
            'n:'
            'u:'
            'c:'
            'l:'
            'r:'
            'a:'
        ),
        [
            'help',
            'tests=',
            'name=',
            'underlay_config=',
            'client=',
            'client-auth=',
            'client-args=',
            'log-dir=',
            'debug',
            'results-dir=',
            'debug-test'
        ])

    # Defaults
    client_impl_type = 'neutron'
    client_auth_type = 'noauth'
    client_args = {}
    tests = ''
    underlay_config = z_con.DEFAULT_UNDERLAY_CONFIG
    debug = False
    test_debug = False
    log_dir = '/tmp/zephyr/logs'
    results_dir = '/tmp/zephyr/results'
    topology = '2z-3c-2edge.json'
    name = datetime.datetime.utcnow().strftime('%Y_%m_%d_%H-%M-%S')

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-t', '--tests'):
            if value == '':
                usage(ArgMismatchException(
                    'Tests should be given as a comma-delimited list '
                    'with no spaces'))
            tests = value.split(',')
        elif arg in ('-n', '--name'):
            name = value
        elif arg in ('-u', '--underlay-config'):
            underlay_config = value
        elif arg in ('-c', '--client'):
            client_impl_type = value
        elif arg in ('-a', '--client-auth'):
            client_auth_type = value
        elif arg in ('-l', '--log-dir'):
            log_dir = value
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in '--debug-test':
            test_debug = True
        elif arg in ('-r', '--results-dir'):
            results_dir = value
        elif arg == '--client-args':
            for kv in value.split(','):
                if kv == '':
                    usage(ArgMismatchException(
                        'Client args should be key=value pairs, '
                        'with one "=", separated by "," and no spaces.'))

                p = kv.split('=')
                if len(p) != 2:
                    usage(ArgMismatchException(
                        'Client args should be key=value pairs, with '
                        'one "=", separated by "," and no spaces.'))
                client_args[p[0]] = p[1]
        else:
            raise ArgMismatchException('Invalid argument' + arg)

    if len(tests) == 0:
        usage(ArgMismatchException(
            'Must specify at least one test with the -t or --tests option'))

    tsm_run_dir = os.path.dirname(os.path.abspath(__file__))

    z_con.ZephyrInit.init(tsm_run_dir + "/zephyr.conf")
    root_dir = z_con.ZephyrInit.BIN_ROOT_DIR
    print('Setting root dir to: ' + root_dir)

    client_impl = None
    base_client_args = dict()
    if client_impl_type == 'neutron':
        if client_auth_type == 'keystone':
            base_client_args = {
                'auth_strategy': 'keystone',
                'auth_url':
                    os.environ.get('OS_ATUH_URL',
                                   'http://localhost:5000/v2.0'),
                'username': os.environ.get('OS_USERNAME', 'admin'),
                'password': os.environ.get('OS_PASSWORD', 'cat'),
                'tenant_name': os.environ.get('OS_TENANT_NAME', 'admin')}
        base_client_args.update(client_args)
        client_impl = create_neutron_client(**base_client_args)
    else:
        raise ArgMismatchException(
            'Invalid client API implementation:' + client_impl_type)

    print('Setting up log manager with debug=' + str(debug))
    log_manager = LogManager(root_dir=log_dir)
    console_log = log_manager.add_stdout_logger(
        name='tsm-run-console',
        log_level=logging.DEBUG if debug is True else logging.INFO)
    log_manager.rollover_logs_fresh(file_filter='*.log')

    # TODO(micucci): This will take a map specifying how to create VMs
    # instead of a PTM
    console_log.debug('Setting up vtm')
    vtm = VirtualTopologyManager(
        client_api_impl=client_impl,
        log_manager=log_manager)
    vtm.configure_logging(debug=debug)
    vtm.read_underlay_config(underlay_config)

    console_log.debug('Setting up tsm')
    tsm = TestSystemManager(vtm, log_manager=log_manager)
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
            print('Passed [{0}/{1}]'.format(
                len(result.successes), result.testsRun))
            print('Expected Failures [{0}/{1}]'.format(
                len(result.expectedFailures), result.testsRun))
            print('Failed [{0}/{1}]'.format(
                len(result.failures), result.testsRun))
            print('Error [{0}/{1}]'.format(
                len(result.errors), result.testsRun))
            print('')
            for tc, err in result.failures:
                print('------------------------------')
                print('Test Case FAILED: [' + tc.get_name() + ']')
                print('Failure Message:')
                print(err)

            for tc, err in result.expectedFailures:
                print('------------------------------')
                print('Test Case passed with EXPECTED FAILURE: [' +
                      tc.get_name() +
                      '], see issue(s) [' +
                      ','.join(tc.expected_failure_issue_ids) + ']')
                print('Failure Message:')
                print(err)

            for tc, err in result.errors:
                if isinstance(tc, TestCase):
                    print('------------------------------')
                    print('Test Case ERROR: [' + tc.get_name() + ']')
                    print('Error Message:')
                    print(err)
                else:
                    print('------------------------------')
                    print('Test Framework ERROR')
                    print('Error Message:')
                    print(err)

            for tc, err in result.skipped:
                print('------------------------------')
                print('Test Case SKIPPED: [' + tc.get_name() + ']')
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
