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
import CBT.EnvSetup as env
import CBT.VersionConfig as version_config

import traceback

CONTROL_CMD_NAME = 'cbt-ctl.py'


def usage(except_obj):
    print 'Usage: cbt-ctl.py {-i <component> | -u <component>} [-V <version>] [-D <distro>]'
    print '                  [-S <repo_server>] [-U <username>] [-P <password>] [-d]'
    print 'Available Components:'
    print '                  midonet - Midolman OSS packages'
    print '                  midonet-mem - Midolman MEM packages'
    print '                  plugin - Midonet python plugin for OpenStack'
    print '                  neutron - OpenStack Neutron component'
    print 'Versions:'
    print '                  These are of the form: [E:]X.Y[.Z][(~|-)T] where E is epoch, X is major, Y is minor, '
    print '                  Z is patch number, and T is an optional tag identifier:'
    print '                          1.X.Y - MEM only'
    print '                          2014.X[.Y]/2015.X[.Y] - OSS only'
    print '                          >5.X[.Y] - MEM/OSS using ZOOM architecture'
    print '                          master - Current, nightly packages'
    print 'Distributions:'
    print '                  unstable - Not yet tested'
    print '                  testing - Tested with automated system; awaiting manual scenario testing'
    print '                  rc - Release Candidates'
    print '                  stable - Tested and released'
    if except_obj is not None:
        raise except_obj

try:

    arg_map, extra_args = getopt.getopt(sys.argv[1:], 'hdi:u:V:S:U:P:D:',
                                        ['help', 'debug', 'uninstall=', 'install=', 'server=',
                                         'version=', 'user=', 'pass=', 'dist=', 'distribution='])

    # Defaults
    command = ''

    version = None
    exact_version = None
    distribution = 'stable'
    username = None
    password = None
    log_dir = '/tmp/zephyr/logs'
    debug = False
    component = ''
    server = env.artifactory_server

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-i', '--install'):
            command = 'install'
            component = value
        elif arg in ('-u', '--uninstall'):
            command = 'uninstall'
            component = value
        elif arg in ('-V', '--version'):
            if value != 'master':
                exact_version = value
                version = version_config.parse_midolman_version(value)
        elif arg in ('-D', '--dist', '--distribution'):
            distribution = value
        elif arg in ('-U', '--user'):
            username = value
        elif arg in ('-P', '--pass'):
            password = value
        elif arg in ('-S', '--server'):
            server = value
        elif arg in ('-d', '--debug'):
            debug = True
        else:
            raise ArgMismatchException('Invalid argument' + arg)

    if command == 'install':
        print('Installing ' + component)
        env.install_component(component, server, username, password,
                              version, distribution, exact_version)

    elif command == 'uninstall':
        print('Uninstalling ' + component)
        env.uninstall_component(component, server, username, password,
                                version, distribution, exact_version)
    else:
        raise ArgMismatchException('Command option not recognized: ' + command)

except getopt.GetoptError as e:
    usage(None)
    print "Invalid Command Line: " + e.msg
    exit(1)
except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    usage(None)
    print 'Argument mismatch: ' + str(a)
    #traceback.print_tb(sys.exc_traceback)
    exit(2)
except ObjectNotFoundException as e:
    print 'Object not found: ' + str(e)
    #traceback.print_tb(sys.exc_traceback)
    exit(2)
except SubprocessFailedException as e:
    print 'Subprocess failed to execute: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print 'Unknown exception: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
