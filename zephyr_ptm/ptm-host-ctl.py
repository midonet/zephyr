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

import getopt
import os
import sys
import traceback

from zephyr.common.exceptions import *
from zephyr.common.log_manager import LogManager
from zephyr.common import zephyr_constants
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager
from zephyr_ptm.ptm import ptm_constants


def usage(except_class):
    print('Usage: ' + ptm_constants.HOST_CONTROL_CMD_NAME +
          ' [-h] [-d] [-l <log_dir>] -c <command> -j <host_json>')
    if except_class is not None:
        raise except_class

try:

    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'hdc:j:l:a:f:',
        ['help', 'debug', 'command=', 'host-json=', 'app-json=', 'log-dir=',
         'log-file='])

    # Defaults
    host_cmd = ''
    host_json = ''
    app_json = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False
    log_file = zephyr_constants.ZEPHYR_LOG_FILE_NAME

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in ('-c', '--command'):
            host_cmd = value
        elif arg in ('-j', '--host-json'):
            host_json = value
        elif arg in ('-a', '--app-json'):
            app_json = value
        elif arg in ('-l', '--log-dir'):
            log_dir = value
        elif arg in ('-f', '--log-file'):
            log_file = value
        else:
            usage(ArgMismatchException('Invalid argument' + arg))

    if host_cmd == '':
        usage(ArgMismatchException('Must specify command to host'))

    if host_json == '':
        usage(ArgMismatchException('Must specify JSON representing host'))

    if app_json == '':
        usage(ArgMismatchException(
            'Must specify JSON representing application'))

    arg_list = extra_args

    ptm_ctl_dir = os.path.dirname(os.path.abspath(__file__))

    zephyr_constants.ZephyrInit.init(ptm_ctl_dir + "/../zephyr.conf")
    root_dir = zephyr_constants.ZephyrInit.BIN_ROOT_DIR
    print('Setting root dir to: ' + root_dir)

    log_manager = LogManager(root_dir=log_dir)

    ptm = PhysicalTopologyManager(root_dir=root_dir,
                                  log_manager=log_manager)
    ptm.configure_logging(
        log_file_name=log_file, debug=debug)
    ptm.ptm_host_app_control(host_cmd, host_json, app_json, arg_list)

except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print('Argument mismatch: ' + str(a))
    usage(None)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except ObjectNotFoundException as e:
    print('Object not found: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except SubprocessFailedException as e:
    print('Subprocess failed to execute: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print('Unknown exception: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
