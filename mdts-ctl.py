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
import json

from common.Exceptions import *
from PTM.MapConfigReader import MapConfigReader
from PTM.RootServer import RootServer
from common.CLI import CONTROL_CMD_NAME
from CBT.EnvSetup import EnvSetup
import traceback

def usage(exceptClass):
    print 'Usage: ' + CONTROL_CMD_NAME + ' {boot|init|start|stop|shutdown|config} [options]'
    print 'Usage: ' + CONTROL_CMD_NAME + ' neutron {install} [options]'
    if exceptClass is not None:
        raise exceptClass()

try:

    if len(sys.argv) < 2:
        usage(ExitCleanException)
    else:
        cmd = sys.argv[1]
        with open('config.json', 'r') as f:
            config_obj = json.load(f)

        config = MapConfigReader.get_physical_topology_config(config_obj)
        os_host = RootServer.create_from_physical_topology_config(config)
        os_host.init()

        if cmd == 'neutron':
            if len(sys.argv) < 3:
                usage(ExitCleanException)
            if sys.argv[2] == 'install':
                EnvSetup.install_neutron_client()
        elif cmd == 'boot':
            os_host.setup()
        elif cmd == 'init':
            os_host.prepare_files()
        elif cmd == 'start':
            os_host.start()
        elif cmd == 'stop':
            os_host.stop()
        elif cmd == 'shutdown':
            os_host.cleanup()
        elif cmd == 'config':
            os_host.print_config()
        elif cmd == 'control':
            os_host.control(*sys.argv[2:])
        else:
            raise ArgMismatchException(' '.join(sys.argv[1:]))
   
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
except MDTSException as e:
    print 'Unknown exception: ' + str(e)
    traceback.print_tb(sys.exc_traceback)
    exit(2)
