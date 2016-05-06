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

from zephyr.common.cli import LinuxCLI
from zephyr.common import exceptions
from zephyr.common.log_manager import LogManager
from zephyr_ptm.ptm.application import hypervisor_service
from zephyr_ptm.ptm.config import version_config
from zephyr_ptm.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager
from zephyr_ptm.ptm import ptm_constants


# noinspection PyUnresolvedReferences
def usage(except_obj):
    print('Usage: ' + ptm_constants.CONTROL_CMD_NAME +
          ' {--startup|--shutdown|--print|--features|--json} '
          '[--config-file <JSON file>]')
    if except_obj is not None:
        raise except_obj


def print_json(pt_imp):
    print ("{")
    print ("api_url: " +
           version_config.ConfigMap.get_configured_parameter(
               'param_midonet_api_url'))
    print ("hypervisors: [")
    for h in pt_imp.hosts_by_name.itervalues():
        for app in h.applications:
            if isinstance(app, hypervisor_service.HypervisorService):
                print("  {")
                print("    host: " + h.name + ",")
                print("    ip: " + app.get_communication_ip() + ",")
                print("    method: mm_ctl")
                print("  },")
    print("]")
    print("}")


try:

    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'hdpc:l:fj',
        ['help', 'debug', 'startup', 'shutdown',
         'print', 'features', 'config-file=',
         'log-dir=', 'json'])

    # Defaults
    command = ''
    ptm_config_file = '2z-3c-2edge.json'
    neutron_command = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-d', '--debug'):
            debug = True
        elif arg in '--startup':
            command = 'startup'
        elif arg in '--shutdown':
            command = 'shutdown'
        elif arg in ('-c', '--config-file'):
            ptm_config_file = value
        elif arg in ('-l', '--log-dir'):
            log_dir = value
        elif arg in ('-p', '--print'):
            command = 'print'
        elif arg in ('-f', '--features'):
            command = 'features'
        elif arg in ('-j', '--json'):
            command = 'json'
        else:
            usage(exceptions.ArgMismatchException('Invalid argument' + arg))

    if command == '':
        usage(exceptions.ArgMismatchException(
            'Must specify at least one command option'))

    root_dir = os.getenv("PYTHONPATH", LinuxCLI().cmd('pwd').stdout.strip())
    LinuxCLI().cmd('pwd').stdout.strip()

    log_manager = LogManager(root_dir=log_dir)
    if command == 'startup':
        log_manager.rollover_logs_fresh(file_filter='ptm*.log')

    ptm_impl = ConfiguredHostPTMImpl(root_dir=root_dir,
                                     log_manager=log_manager)
    ptm_impl.configure_logging(debug=debug)

    ptm = PhysicalTopologyManager(ptm_impl)
    ptm.configure(ptm_config_file)

    if command == 'startup':
        ptm.startup()
        print_json(ptm_impl)
    elif command == 'shutdown':
        ptm.shutdown()
    elif command == 'print':
        ptm.print_config()
    elif command == 'features':
        ptm.print_features()
    elif command == 'json':
        print_json(ptm_impl)
    else:
        usage(exceptions.ArgMismatchException(
            'Command option not recognized: ' + command))

except exceptions.ExitCleanException:
    exit(1)
except exceptions.ArgMismatchException as a:
    print('Argument mismatch: ' + str(a))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except exceptions.ObjectNotFoundException as e:
    print('Object not found: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except exceptions.SubprocessFailedException as e:
    print('Subprocess failed to execute: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except exceptions.TestException as e:
    print('Unknown exception: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
