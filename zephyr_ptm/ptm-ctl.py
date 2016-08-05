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
import json
import os
import sys
import traceback

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common.log_manager import LogManager
from zephyr.common import zephyr_constants as zc
from zephyr_ptm.ptm.config import version_config
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager


def usage(except_obj):
    und_file = zc.DEFAULT_UNDERLAY_CONFIG
    print("Usage: ptm-ctl.py --startup [-c <config_file>] [-d]")
    print("       ptm-ctl.py --shutdown [-d]")
    print("       ptm-ctl.py --print")
    print("       ptm-ctl.py --features")
    print("       ptm-ctl.py --json")
    print('')
    print("Commands:")
    print("    --startup")
    print("        Starts up an underlay topology.  Use -c or --config-file")
    print("        to specify a PTM config file with a proper PTM-config")
    print("        JSON representing the underlay topology.  This file can be")
    print("        an absolute path, or a path relative from the")
    print("        zephyr_ptm/config/physical_topologies directory.  This")
    print("        will also output the zephyr general underlay configuration")
    print("        JSON to a file named: " + und_file + " in the current")
    print("        directory.")
    print("        Use -d or --debug for debug information to be logged.")
    print("    --shutdown")
    print("        Shuts down the existing underlay topology defined in the")
    print("        zephyr underlay: " + und_file + ".  This file will be")
    print("        used to shut down the system, so it must be accurate and")
    print("        current.")
    print("        Use -d or --debug for debug information to be logged.")
    print("    --print")
    print("        Prints the existing underlay topology defined in the")
    print("        zephyr underlay: " + und_file + ".  This file will be")
    print("        used to display the configuration of the system, so it")
    print("        must be accurate and current.")
    print("    --features")
    print("        Prints a list of the existing underlay supported")
    print("        topology features for the topology defined in the current")
    print("        zephyr underlay: " + und_file + ".  This file will be")
    print("        used to inform the configuration of the system, so it")
    print("        must be accurate and current.")
    print("    --json")
    print("        Prints the existing underlay topology defined in the")
    print("        zephyr underlay: " + und_file + ".  This file will be")
    print("        used to display the underlay topology of the currently")
    print("        running system, so it must be accurate and current.")

    if except_obj is not None:
        raise except_obj


def print_json(ptm_imp, dbg_on, log_base_dir, output_file=None):
    config_map = {
        'debug': dbg_on,
        'log_dir': log_base_dir,
        'ptm_log_file': ptm_imp.log_file_name,
        'underlay_system':
            "zephyr_ptm.ptm.underlay.ptm_underlay_system.PTMUnderlaySystem",
        'topology_config_file': ptm_imp.topo_file,
        'root_dir': ptm_imp.root_dir,
        'api_url':
            version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url')
    }
    out_str = json.dumps(config_map)
    if output_file:
        with open(output_file, 'w') as fp:
            fp.write(out_str)
    else:
        print(out_str)

try:
    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'hdpc:l:fju:',
        ['help', 'debug', 'startup', 'shutdown',
         'print', 'features', 'config-file=',
         'log-dir=', 'json'])

    # Defaults
    ptm_ctl_dir = os.path.dirname(os.path.abspath(__file__))

    zc.ZephyrInit.init(ptm_ctl_dir + "/../zephyr.conf")
    root_dir = zc.ZephyrInit.BIN_ROOT_DIR
    conf_dir = zc.ZephyrInit.CONF_ROOT_DIR

    command = ''
    ptm_topo = '1z-2c-1edge.json'
    neutron_command = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False
    underlay_config_file = conf_dir + '/' + zc.DEFAULT_UNDERLAY_CONFIG

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
            ptm_topo = value
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

    log_manager = LogManager(root_dir=log_dir)
    if command == 'startup':
        log_manager.rollover_logs_fresh(file_filter='ptm*.log')

    ptm = PhysicalTopologyManager(root_dir=root_dir,
                                  log_manager=log_manager)
    ptm.configure_logging(debug=debug)

    if cli.LinuxCLI().exists(underlay_config_file):
        with open(underlay_config_file, "r") as f:
            ptm_underlay_map = json.load(f)
        ptm_topo = ptm_underlay_map['topology_config_file']

    ptm.configure(ptm_topo)

    if command == 'startup':
        ptm.startup()
        print_json(ptm, debug, log_dir, underlay_config_file)
    elif command == 'shutdown':
        ptm.shutdown()
        cli.LinuxCLI().rm(underlay_config_file)
    elif command == 'print':
        ptm.print_config()
    elif command == 'features':
        ptm.print_features()
    elif command == 'json':
        print_json(ptm, debug, log_dir)
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
