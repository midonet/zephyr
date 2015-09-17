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


class PackageRepo(object):
    def __init__(self):
        """
        Create a new package repo with the parameterized values.
        :type repo_scheme: str
        :type repo_server: str
        :type repo_dir: str
        :type repo_user: str
        :type repo_pass: str
        :type version: Version
        :type subdir: str
        :return:
        """

    def create_repo_file(self, component, repo_scheme, repo_server, repo_dir,
                         repo_user=None, repo_pass=None,
                         subdir='master/stable'):
        """
        Create the repository config file on the OS for the given component
        :type component: str
        :return:
        """
        pass

    def install_packages(self, packages, exact_version=None):
        """
        Install the given packages on the OS from the repo
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        pass

    def uninstall_packages(self, packages, exact_version=None):
        """
        Uninstall the given packages from the OS
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        pass

    def is_installed(self, packages):
        """
        Return true if the given packages are installed on the system, false if not
        :type packages: list[str]
        :return: bool
        """
        return False

    @staticmethod
    def get_os_repo():
        """
        Returns a proper repo for the given parameters and the base OS (debian, rpm, etc.)
        :return: PackageRepo
        """
        if version_config.get_linux_dist() == version_config.LINUX_CENTOS:
            repo = RPMPackageRepo()
        elif version_config.get_linux_dist() == version_config.LINUX_UBUNTU:
            repo = DebianPackageRepo()
        else:
            raise ArgMismatchException("Only supported on CentOS or Ubuntu")
        return repo


class DebianPackageRepo(PackageRepo):
    def create_repo_file(self, component, repo_scheme, repo_server, repo_dir,
                         repo_user=None, repo_pass=None,
                         subdir='master/stable'):
        cli = LinuxCLI()

        url_line = repo_scheme + "://"
        if repo_scheme == 'https':
            if repo_user is not None:
                url_line += repo_user
                if repo_pass is not None:
                    url_line += ':' + repo_pass
                url_line += '@'
        url_line += repo_server + '/' + repo_dir

        cli.write_to_file('/etc/apt/sources.list.d/midokura.' + component + '.list',
                          'deb ' + url_line + ' ' + subdir + ' main\n',
                          append=False)
        cli.cmd('curl -k http://artifactory-dev.bcn.midokura.com/artifactory/api/gpg/key/public | apt-key add -')
        cli.cmd('apt-get update')


    def install_packages(self, packages, exact_version=None):
        """
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        cli = LinuxCLI()
        pkg_list = ' '.join(map(lambda v: v + (('=' + exact_version) if exact_version is not None else ''),
                                packages))
        print 'Installing Debian packages: ' + pkg_list
        cli.cmd('apt-get install -y ' + pkg_list)


    def uninstall_packages(self, packages, exact_version=None):
        """
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        cli = LinuxCLI()
        pkg_list = ' '.join(map(lambda v: v + (('=' + exact_version) if exact_version is not None else ''),
                                packages))
        print 'Uninstalling Debian packages: ' + pkg_list
        ret = cli.cmd('apt-get remove -y ' + pkg_list)

    def is_installed(self, package):
        cli = LinuxCLI()
        if not cli.grep_cmd('dpkg -l', package):
            return False
        return True

class RPMPackageRepo(PackageRepo):
    def create_repo_file(self, component, repo_scheme, repo_server, repo_dir,
                         repo_user=None, repo_pass=None,
                         subdir='master/stable'):
        cli = LinuxCLI()

    def install_packages(self, package, exact_version=None):
        """
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        cli = LinuxCLI()
        cli.cmd('yum install -y ' + package + ('-' + exact_version if exact_version is not None else ''))

    def uninstall_packages(self, package, exact_version=None):
        """
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        pass

    def is_installed(self, packages):
        cli = LinuxCLI()
        return False
