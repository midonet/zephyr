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
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.ptm_constants import CONTROL_CMD_NAME
from common.CLI import LinuxCLI
from common.LogManager import LogManager


def usage(exceptObj):
    print 'Usage: ' + CONTROL_CMD_NAME + ' {--startup|--shutdown|--print|--features} [--config-file <JSON file>]'
    if exceptObj is not None:
        raise exceptObj

try:

    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hdpc:l:f',
                                        ['help', 'debug', 'startup', 'shutdown', 'print', 'features', 'config-file=',
                                         'log-dir='])

    # Defaults
    command = ''
    ptm_config_file = 'config/physical_topologies/2z-2c-2edge.json'
    neutron_command = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in ('--startup'):
            command = 'startup'
        elif arg in ('--shutdown'):
            command = 'shutdown'
        elif arg in ('-c', '--config-file'):
            ptm_config_file = value
        elif arg in ('-l', '--log-dir'):
            log_dir = value
        elif arg in ('-p', '--print'):
            command = 'print'
        elif arg in ('-f', '--features'):
            command = 'features'
        else:
            usage(ArgMismatchException('Invalid argument' + arg))

    if command == '':
        usage(ArgMismatchException('Must specify at least one command option'))

    root_dir = LinuxCLI().cmd('pwd').stdout.strip()

    log_manager = LogManager(root_dir=log_dir)
    if command == 'startup':
        log_manager.rollover_logs_fresh(file_filter='ptm*.log')

    ptm_impl = ConfiguredHostPTMImpl(root_dir=root_dir, log_manager=log_manager)
    ptm_impl.configure_logging(debug=debug)

    ptm = PhysicalTopologyManager(ptm_impl)
    ptm.configure(ptm_config_file)

    if command == 'startup':
        ptm.startup()
    elif command == 'shutdown':
        ptm.shutdown()
    elif command == 'print':
        ptm.print_config()
    elif command == 'features':
        ptm.print_features()
    else:
        usage(ArgMismatchException('Command option not recognized: ' + command))

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
