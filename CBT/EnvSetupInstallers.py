__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import CBT.VersionConfig as version_config
from common.Exceptions import *
from common.CLI import LinuxCLI


class ComponentInstaller(object):
    def __init__(self, version=None):
        """
        Version object represents the version to install, or None to use master distribution
        :type version: Version
        :return:
        """
        self.version = version

    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                         version=None, distribution='stable'):
        """
        Returns the proper repo given the parameters, which will access and install
        the component.
        :type repo: PackageRepo
        :type scheme: str
        :type server: str
        :type main_dir: str
        :type username: str
        :type password: str
        :type version: Version
        :type distribution: str
        :return:
        """
        pass

    def install_packages(self, repo, exact_version=None):
        """
        Install the component packages via the given repo.  The exact_version field can be used to
        pinpoint an exact version in the repo, if necessary.
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        pass

    def uninstall_packages(self, repo, exact_version=None):
        """
        Same as install, but remove packages instead.
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        pass


class MidonetComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                 version=None, distribution='stable'):
        sub_dir = ('master' if version is None else version.major + '.' + version.minor) + '/' + distribution
        return repo.create_repo_file('midonet', scheme, server, main_dir, username, password, sub_dir)

    def get_pkg_list(self):
        config_map = version_config.ConfigMap.get_config_map()
        """ :type: dict [str, str]"""
        major_version = config_map["master_major_version"] if self.version is None else self.version.major

        if major_version not in config_map:
            raise ArgMismatchException("Major version not found in config map: " + major_version)
        package_list = config_map[major_version]["installed_packages"]
        return package_list

    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.install_packages(self.get_pkg_list(), exact_version)

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.uninstall_packages(self.get_pkg_list(), exact_version)


class MidonetUtilsComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                         version=None, distribution='stable'):
        sub_dir = 'thirdparty'
        return repo.create_repo_file('midonet-3rdparty', scheme, server, main_dir, username, password, sub_dir)


    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.install_packages(['zkdump'])

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.uninstall_packages(['zkdump'])

    def is_installed(self, repo):
        return repo.is_installed(['zkdump'])


class PluginComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                         version=None, distribution='stable'):
        sub_dir = ('master' if version is None else version.major) + '/' + distribution
        return repo.create_repo_file('networking-midonet', scheme, server, main_dir, username, password, sub_dir)

    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        #TODO: Plugin's exact version is a little different from the version in the repo
        repo.install_packages(['python-neutron-plugin-midonet'])

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.uninstall_packages(['python-neutron-plugin-midonet'])

    def is_installed(self, repo):
        return repo.is_installed(['python-neutron-plugin-midonet'])


class NeutronComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                         version=None, distribution='stable'):
        return None

    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """

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
        #cli.add_environment_variable('MIDONET_ENABLE_Q_SVC_ONLY', 'True')
        cli.add_environment_variable('LOG_COLOR', 'False')
        cli.add_environment_variable('LOGDIR', cli_safe.cmd('echo `pwd`/logs').strip('\n'))
        cli.add_environment_variable('SCREEN_LOGDIR', cli_safe.cmd('echo `pwd`/logs').strip('\n'))
        cli.add_environment_variable('LOGFILE', cli_safe.cmd('echo `pwd`/logs/stack.sh.log').strip('\n'))
        #cli.add_environment_variable('NEUTRON_REPO', 'http://github.com/tomoe/neutron')
        #cli.add_environment_variable('NEUTRON_BRANCH', 'midonet1')
    
        plugin_url = 'https://github.com/openstack/networking-midonet release/kilo'
        #plugin_url = 'http://openstack./tomoe/networking-midonet.git midonet1'
        cf_str = '#!/usr/bin/env bash\n' \
                 '[[local|localrc]]\n' \
                 '\n' \
                 'ENABLED_SERVICES=rabbit,mysql,key\n' \
                 'ENABLED_SERVICES+=,q-svc,neutron\n' \
                 'ENABLED_SERVICES+=,q-lbaas\n' \
                 'enable_plugin networking-midonet ' + plugin_url + '\n'
        LinuxCLI().write_to_file('devstack/local.conf', cf_str, False)
    
        if cli.cmd('cd devstack ; ./stack.sh', return_status=True) is not 0:
            raise SubprocessFailedException('devstack/stack.sh')
    
        LinuxCLI().regex_file('/etc/midolman/midolman.conf', 's/\(enabled = \)true/\1false/')


    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        pass

    def is_installed(self, repo):
        return repo.is_installed(['python-neutron'])

