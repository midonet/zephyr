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
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.host import vm_host
from zephyr_ptm.ptm.physical_topology_manager import PhysicalTopologyManager
from zephyr_ptm.ptm import ptm_utils


def usage(except_obj):
    print("Usage: ptm-utils.py {command} {parameters}")
    print('')
    print("Command can be one of:")
    print("    --add-vm, --add-interface, --start-apps, --restart-apps,")
    print("    --stop-apps, --bind-port, --unbind-port")
    print('')
    print("Parameters for the different commands:")
    print("    Parameters should all be separated by commas with no spaces")
    print("    --add-vm")
    print("        Add a new IP Net Namespace-based VM on a comptue host")
    print("        Params: 'compute,name,port'")
    print("            compute: The compute host to start the VM on")
    print("            name: Name of the VM")
    print("            IP: IP to set on the VM")
    print("            port: Network overlay port to bind to the VM's 'eth0'")
    print('')
    print("  --add-interface")
    print("        Add an 'eth0' interface to an existing VM")
    print("        Params: 'compute,vm_name,IP'")
    print("            compute: The compute host the VM is on")
    print("            name: Name of the VM")
    print("            IP: IP to set on the VM")
    print('')
    print("  --start-apps")
    print("        Start configured applications on given host")
    print("        Params: 'host'")
    print("            host: Host to start applications on")
    print('')
    print("  --restart-apps")
    print("        Restart configured applications on given host")
    print("        Params: 'host'")
    print("            host: Host to restart applications on")
    print('')
    print("  --stop-apps")
    print("        Stop configured applications on given host")
    print("        Params: 'host'")
    print("            host: Host to stop applications on")
    print('')
    print("  --bind-port")
    print("        Bind interface on a host to a port on the network overlay")
    print("        Params: 'host,iface,port'")
    print("            host: Host to perform the bind request")
    print("            iface: Interface to bind to the network overlay")
    print("            port: Port on the network overlay to bind")
    print('')
    print("  --unbind-port")
    print("        Unplud a port from the network overlay")
    print("        Params: 'host,port'")
    print("            host: Host to unplug port from")
    print("            port: Port to be unplugged from the network overlay")
    if except_obj is not None:
        raise except_obj


commands = ['add-vm', 'del-vm', 'add-interface',
            'start-apps', 'restart-apps', 'stop-apps',
            'bind-port', 'ubind-port']
try:

    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'h',
        [c + '=' for c in commands] +
        ['help'])

    # Defaults

    ptm_ctl_dir = os.path.dirname(os.path.abspath(__file__))

    zc.ZephyrInit.init(ptm_ctl_dir + "/../zephyr.conf")
    root_dir = zc.ZephyrInit.BIN_ROOT_DIR
    conf_dir = zc.ZephyrInit.CONF_ROOT_DIR
    print('Setting bin root dir to: ' + root_dir +
          ' and config dir to: ' + conf_dir)

    command = None
    params = []
    underlay_config_file = conf_dir + '/' + zc.DEFAULT_UNDERLAY_CONFIG

    log_dir = '/tmp/zephyr/logs'

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in map(lambda cmd: '--' + cmd, commands):
            command = arg[2:]
            params = value.split(',')
        else:
            usage(exceptions.ArgMismatchException('Invalid argument' + arg))

    if not command:
        usage(exceptions.ArgMismatchException(
            'Must specify at least one command'))

    with open(underlay_config_file, "r") as f:
        ptm_underlay_map = json.load(f)

    if (ptm_underlay_map['underlay_system'] !=
            'zephyr_ptm.ptm.underlay.ptm_underlay_system.PTMUnderlaySystem'):
        raise exceptions.ArgMismatchException(
            "PTM underlay required for this tool")

    ptm_config_file = ptm_underlay_map['topology_config_file']

    log_manager = LogManager(root_dir=log_dir)

    ptm = PhysicalTopologyManager(root_dir=root_dir,
                                  log_manager=log_manager)
    ptm.configure_logging(
        log_file_name=zc.ZEPHYR_LOG_FILE_NAME, debug=True)

    ptm.configure(ptm_config_file)

    print("Running command: " + command)

    if command == 'restart-apps':
        if len(params) == 0:
            raise exceptions.ArgMismatchException(
                "The 'host' parameter is required for restart-apps command")
        host_obj = ptm.hosts_by_name[params[0]]
        host_obj.restart_apps()

    elif command == 'start-apps':
        if len(params) == 0:
            raise exceptions.ArgMismatchException(
                "The 'host' parameter is required for start-apps command")
        host_obj = ptm.hosts_by_name[params[0]]
        host_obj.start_applications()
        host_obj.wait_for_all_applications_to_start()

    elif command == 'stop-apps':
        if len(params) == 0:
            raise exceptions.ArgMismatchException(
                "The 'host' parameter is required for stop-apps command")
        host_obj = ptm.hosts_by_name[params[0]]
        host_obj.stop_applications()
        host_obj.wait_for_all_applications_to_stop()

    elif command == 'bind-port':
        if len(params) < 3:
            raise exceptions.ArgMismatchException(
                "The 'host', 'iface', and 'port' parameters are required for "
                "bind-port command")
        host_obj = ptm.hosts_by_name[params[0]]
        iface = params[1]
        port = params[2]
        app_type = application.APPLICATION_TYPE_HYPERVISOR
        app_obj = host_obj.applications_by_type[app_type][0]
        """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV """
        app_obj.plugin_iface_to_network(
            tap_iface=iface, port_id=port)

    elif command == 'unbind-port':
        if len(params) < 2:
            raise exceptions.ArgMismatchException(
                "The 'host' and 'port' parameters are required for "
                "unbind-port command")
        host_obj = ptm.hosts_by_name[params[0]]
        port = params[1]
        app_type = application.APPLICATION_TYPE_HYPERVISOR
        app_obj = host_obj.applications_by_type[app_type][0]
        """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV """
        app_obj.disconnect_port(port_id=port)

    elif command == "add-vm":
        if len(params) < 3:
            raise exceptions.ArgMismatchException(
                "The 'compute', 'vm_name', and 'port' parameters "
                "are required for add-vm command")
        host = params[0]
        host_obj = ptm.hosts_by_name[host]
        app_type = application.APPLICATION_TYPE_HYPERVISOR
        app_obj = host_obj.applications_by_type[app_type][0]
        """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV """
        name = params[1]
        port = params[2]

        if not host_obj.is_hypervisor():
            raise exceptions.ArgMismatchException(
                "Must select a hypervisor to start VM")

        new_vm = ptm_utils.create_vm(
            hv_host_obj=host_obj,
            name=name,
            log=ptm.LOG)

        # noinspection PyUnresolvedReferences
        mac = cli.LinuxCLI().cmd(
            "neutron" +
            " --os-url=http://localhost:9696" +
            " --os-token=admin" +
            " --os-auth-url=http://hostname:5000/v2.0" +
            " --os-auth-strategy=noauth" +
            " port-show " +
            port +
            " --tenant-id=admin" +
            " | grep mac_address" +
            " | awk '{ print $4 }'").stdout.strip()

        ptm.LOG.info('VM MAC: ' + mac)
        tapname = 'tap' + port[0:8]
        host_obj.create_tap_interface_for_vm(
            tap_iface_name=tapname, vm_host=new_vm,
            vm_iface_name='eth0', vm_mac=mac)

        app_obj.plugin_iface_to_network(
            tap_iface=tapname, port_id=port)
        ptm_utils.setup_vm_network(
            new_vm, None, None, ptm.LOG)

    elif command == "del-vm":
        if len(params) < 3:
            raise exceptions.ArgMismatchException(
                "The 'compute', 'vm_name/id', and 'port' parameters "
                "are required for add-vm command")
        host = params[0]
        host_obj = ptm.hosts_by_name[host]
        app_type = application.APPLICATION_TYPE_HYPERVISOR
        app_obj = host_obj.applications_by_type[app_type][0]
        """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV """
        name = params[1]
        port = params[2]

        if not host_obj.is_hypervisor():
            raise exceptions.ArgMismatchException(
                "Must select a hypervisor to start VM")

        app_obj.disconnect_port(port_id=port)

        vm_obj = vm_host.VMHost(name, app_obj)
        vm_obj.remove()

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
