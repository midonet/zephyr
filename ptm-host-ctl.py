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
import traceback
import getopt

from common.Exceptions import *
from common.CLI import LinuxCLI
from common.LogManager import LogManager
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.ptm_constants import HOST_CONTROL_CMD_NAME


def usage(exceptClass):
    print 'Usage: ' + HOST_CONTROL_CMD_NAME + ' [-h] [-d] [-l <log_dir>] -c <command> -j <host_json>'
    if exceptClass is not None:
        raise exceptClass

try:

    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hdc:j:l:a:',
                                        ['help', 'debug', 'command=', 'host-json=', 'app-json=', 'log-dir='])

    # Defaults
    host_cmd = ''
    host_json = ''
    app_json = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False

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
        else:
            usage(ArgMismatchException('Invalid argument' + arg))

    if host_cmd == '':
        usage(ArgMismatchException('Must specify command to host'))

    if host_json == '':
        usage(ArgMismatchException('Must specify JSON representing host'))

    if app_json == '':
        usage(ArgMismatchException('Must specify JSON representing application'))

    arg_list = extra_args

    root_dir = LinuxCLI().cmd('pwd').stdout.strip()

    log_manager = LogManager(root_dir=log_dir)

    ptm_impl = ConfiguredHostPTMImpl(root_dir=root_dir, log_manager=log_manager)
    ptm_impl.configure_logging(debug=debug)
    ptm_impl.ptm_host_app_control(host_cmd, host_json, app_json, arg_list)

except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print 'Argument mismatch: ' + str(a)
    usage(None)
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
