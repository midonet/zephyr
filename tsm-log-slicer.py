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
import json
import pprint
import sys
import traceback

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common import file_location
from zephyr.common import log_slicer


def usage(except_obj):
    print('Usage: tsm-log-slicer.py -r results_dir [-l <leeway>] [-d] ')
    print('')
    print('   Slice Options:')
    print('     -l, --leeway')
    print('         Set leeway time for logs (default +/- 5 seconds).')
    print('   Debug Options:')
    print('     -d, --debug')
    print('         Turn on DEBUG logging (and split log output to stdout).')
    print('   Required Parameters:')
    print('     -r, --results-dir <dir>')
    print('          Results directory for the test run (must have')
    print('          results.json file and full-logs directory).')
    if except_obj is not None:
        raise except_obj


try:
    arg_map, extra_args = getopt.getopt(
        sys.argv[1:],
        (
            'h'
            'd'
            'l:'
            'r:'
        ),
        [
            'help',
            'leeway=',
            'debug',
            'results-dir=',
        ])

    # Defaults
    debug = False
    results_dir = None
    leeway = 5

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-r', '--results-dir'):
            results_dir = value
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in ('-l', '--leeway'):
            leeway = value
        else:
            raise exceptions.ArgMismatchException('Invalid argument' + arg)

    if not results_dir:
        usage(exceptions.ArgMismatchException(
            "Results directory is a required parameter!"))

    print('Reading results from:' + results_dir + '/results.json')
    with open(results_dir + '/results.json', 'r') as fp:
        result_map = json.load(fp)

    print('Read results: ')
    pprint.pprint(result_map)

    log_files = cli.LinuxCLI.ls(results_dir + '/full-logs/*')
    print('Slicing log files: ' + str(log_files))

    for tc in result_map['testsuite']['testcases']:
        start_time = tc["starttime"]
        stop_time = tc["stoptime"]
        tcname = tc["name"]
        print("Creating sliced log-files for test: " + tcname)
        cli.LinuxCLI(priv=False).mkdir(results_dir + '/' + tcname)
        log_slicer.slice_log_files_by_time(
            log_files=[file_location.FileLocation(f) for f in log_files],
            out_dir=results_dir + '/' + tcname,
            slice_start_time=datetime.datetime.strptime(
                start_time, '%Y-%m-%d %H:%M:%S,%f'),
            slice_stop_time=datetime.datetime.strptime(
                stop_time, '%Y-%m-%d %H:%M:%S,%f'),
            leeway=leeway)

except exceptions.ExitCleanException:
    exit(1)
except exceptions.ArgMismatchException as a:
    print('Argument mismatch: ' + str(a))
    exit(2)
except exceptions.ObjectNotFoundException as e:
    print('Object not found: ' + str(e))
    exit(2)
except exceptions.SubprocessFailedException as e:
    print('Subprocess failed to execute: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except exceptions.TestException as e:
    print('Unknown exception: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
