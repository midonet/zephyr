__author__ = 'micucci'
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

from common.CLI import LinuxCLI
from common.Exceptions import SubprocessFailedException

class EnvSetup:
    @staticmethod
    def install_neutron_client():

        cli_safe = LinuxCLI(priv=False)

        if LinuxCLI().exists('devstack') is True:
            cli_safe.cmd('cd devstack ; git pull; cd ..')
        else:
            cli_safe.cmd('git clone http://github.com/openstack-dev/devstack',)

        cli = LinuxCLI(priv=False)

        cli.add_environment_variable('HOME', cli_safe.cmd('echo $HOME').strip('\n'))
        cli.add_environment_variable('PATH', cli_safe.cmd('echo $PATH').strip('\n'))
        cli.add_environment_variable('USER', cli_safe.cmd('echo $USER').strip('\n'))
        cli.add_environment_variable('WORKSPACE', cli_safe.cmd('pwd').strip('\n'))
        cli.add_environment_variable('MIDONET_ENABLE_Q_SVC_ONLY', 'True')
        cli.add_environment_variable('LOG_COLOR', 'False')
        cli.add_environment_variable('LOGDIR',cli_safe.cmd('echo `pwd`/logs'))
        cli.add_environment_variable('SCREEN_LOGDIR',cli_safe.cmd('echo `pwd`/logs'))
        cli.add_environment_variable('LOGFILE',cli_safe.cmd('echo `pwd`/logs/stack.sh.log'))
        cli.add_environment_variable('MIDONET_ENABLE_Q_SVC_ONLY', 'True')
        cli.add_environment_variable('NEUTRON_REPO', 'http://github.com/tomoe/neutron')
        cli.add_environment_variable('NEUTRON_REPO', 'http://github.com/tomoe/neutron')
        cli.add_environment_variable('NEUTRON_BRANCH', 'midonet1')


        cf_str = '#!/usr/bin/env bash\n' \
                 '[[local|localrc]]\n' \
                 '\n' \
                 'enable_plugin networking-midonet http://github.com/tomoe/networking-midonet.git midonet1'
        LinuxCLI().write_to_file('devstack/local.conf', cf_str, False)

        if cli.cmd('cd devstack ; ./stack.sh') is not 0:
            raise SubprocessFailedException('devstack/stack.sh')

        LinuxCLI().regex_file('/etc/midolman/midolman.conf', 's/\(enabled = \)true/\1false/')

