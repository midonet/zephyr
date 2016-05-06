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
import sys
import traceback

from zephyr.common.cli import LinuxCLI
from zephyr.common.exceptions import ArgMismatchException
from zephyr.common.exceptions import ExitCleanException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.exceptions import SubprocessFailedException
from zephyr.common.exceptions import TestException
from zephyr.common.log_manager import LogManager
from zephyr_ptm.ptm.impl.configured_host_ptm_impl import ConfiguredHostPTMImpl
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager
from zephyr_ptm.ptm import ptm_constants


def usage(except_obj):
    print('Usage: ptm-utils.py {--add-vm compute,name,IP[,port]}')
    print('                    {--add-interface compute,vm_name,IP}')
    print('                    {--start-apps host}')
    print('                    {--restart-apps host}')
    print('                    {--stop-apps host}')
    print('                    {--bind-port host,iface,port}')
    print('                    {--unbind-port host,port}')
    if except_obj is not None:
        raise except_obj


commands = ['add-vm', 'add-interface',
            'start-apps', 'restart-apps', 'stop-apps',
            'bind-port', 'ubind-port']
try:

    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'hc:',
        ['config-file=',
         'add-vm=', 'add-interface=',
         'start-apps=', 'restart-apps=', 'stop-apps=',
         'bind-port=', 'unbind-port=',
         'help'])

    # Defaults
    command = None
    params = []
    ptm_config_file = 'ptm/config/physical_topologies/2z-3c-2edge.json'

    log_dir = '/tmp/zephyr/logs'

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in map(lambda c: '--' + c, commands):
            command = arg[2:]
            params = value.split(',')
        elif arg in ('-c', '--config-file'):
            ptm_config_file = value
        else:
            usage(ArgMismatchException('Invalid argument' + arg))

    if not command:
        usage(ArgMismatchException('Must specify at least one command'))

    root_dir = LinuxCLI().cmd('pwd').stdout.strip()

    log_manager = LogManager(root_dir=log_dir)

    ptm_impl = ConfiguredHostPTMImpl(root_dir=root_dir,
                                     log_manager=log_manager)
    ptm_impl.configure_logging(
        log_file_name=ptm_constants.ZEPHYR_LOG_FILE_NAME, debug=True)

    ptm = PhysicalTopologyManager(ptm_impl)
    ptm.configure(ptm_config_file)

    print("Running command: " + command)

    if command == 'restart-apps':
        if len(params) == 0:
            raise ArgMismatchException(
                "The 'host' parameter is required for restart-apps command")
        host_obj = ptm_impl.hosts_by_name[params[0]]
        for app in host_obj.applications:

            so, se = host_obj.run_app_command('stop', app).communicate()
            print("--\n" + so + "--\n" + se + "==")
            so, se = host_obj.run_app_command('start', app).communicate()
            print("--\n" + so + "--\n" + se + "==")
    elif command == 'start-apps':
        if len(params) == 0:
            raise ArgMismatchException(
                "The 'host' parameter is required for start-apps command")
        host_obj = ptm_impl.hosts_by_name[params[0]]
        for app in host_obj.applications:
            so, se = host_obj.run_app_command('start', app).communicate()
            print("--\n" + so + "--\n" + se + "==")
    elif command == 'stop-apps':
        if len(params) == 0:
            raise ArgMismatchException(
                "The 'host' parameter is required for stop-apps command")
        host_obj = ptm_impl.hosts_by_name[params[0]]
        for app in host_obj.applications:
            so, se = host_obj.run_app_command('stop', app).communicate()
            print("--\n" + so + "--\n" + se + "==")
    elif command == 'bind-port':
        if len(params) < 3:
            raise ArgMismatchException(
                "The 'host', 'iface', and 'port' parameters are required for "
                "bind-port command")
        host_obj = ptm_impl.hosts_by_name[params[0]]
        app_obj = host_obj.applications[0]
        so, se = host_obj.run_app_command('bind_port', app_obj,
                                          params[1:]).communicate()
        print("--\n" + so + "--\n" + se + "==")
    elif command == "add-vm":
        if len(params) < 3:
            raise ArgMismatchException(
                "The 'compute', 'vm_name' and 'ip' parameters "
                "are required for add-vm command")
        host = params[0]
        host_obj = ptm_impl.hosts_by_name[host]
        app_obj = host_obj.applications[0]
        name = params[1]
        ip = params[2]
        port = params[3] if len(params) > 3 else None

        new_vm = ptm.create_vm(ip=ip, hv_host=host, name=name)
        if port:
            so, se = host_obj.run_app_command(
                'bind_port', app_obj,
                [host + 'eth0', port]).communicate()

            print("--\n" + so + "--\n" + se + "==")

except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    print('Argument mismatch: ' + str(a))
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
