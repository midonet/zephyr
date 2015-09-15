__author__ = 'micucci'
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

from common.Exceptions import *
from common.CLI import LinuxCLI
from CBT.EnvSetup import EnvSetup
import traceback

CONTROL_CMD_NAME = 'cbt-ctl.py'


def usage(except_obj):
    print 'Usage: ' + CONTROL_CMD_NAME + ' --install <version>'
    print 'Usage: ' + CONTROL_CMD_NAME + ' --uninstall'
    print 'Usage: ' + CONTROL_CMD_NAME + ' --install-neutron <version>'
    if except_obj is not None:
        raise except_obj

try:

    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hi:n:u',
                                        ['help', 'install=', 'uninstall', 'install-neutron='])

    # Defaults
    command = ''
    ptm_config_file = 'config.json'
    neutron_command = ''
    log_dir = '/tmp/zephyr/logs'
    debug = False

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-i', '--install'):
            command = 'install-midonet'
            version = value
        elif arg in ('-u', '--uninstall'):
            command = 'uninstall-midonet'
        elif arg in ('-n', '--install-neutron'):
            command = 'install-neutron'
            version = value
        else:
            usage(ArgMismatchException('Invalid argument' + arg))

    if command == 'install-neutron':
        print('Installing neutron client')
        EnvSetup.install_neutron_client()
    elif command == 'install-midonet':
        pass
    elif command == 'uninstall-midonet':
        pass
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
