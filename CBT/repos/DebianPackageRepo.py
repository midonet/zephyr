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
from CBT.repos.PackageRepo import PackageRepo
from common.Exceptions import *
from common.CLI import LinuxCLI


class DebianPackageRepo(PackageRepo):
    def create_repo_file(self, component, repo_scheme, repo_server, repo_dir,
                         repo_user=None, repo_pass=None,
                         subdir='master/stable'):
        cli = LinuxCLI(log_cmd=True)

        url_line = repo_scheme + "://"
        if repo_scheme == 'https':
            if repo_user is not None:
                url_line += repo_user
                if repo_pass is not None:
                    url_line += ':' + repo_pass
                url_line += '@'
        url_line += repo_server + '/' + repo_dir

        cli.write_to_file('/etc/apt/sources.list.d/' + component + '.list',
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
        cli = LinuxCLI(log_cmd=True)
        pkg_list = ' '.join(map(lambda v: v + (('=' + exact_version) if exact_version is not None else ''),
                                packages))
        print 'Installing Debian packages: ' + pkg_list
        print cli.cmd('apt-get install -y ' + pkg_list)


    def uninstall_packages(self, packages, exact_version=None):
        """
        :type packages: list[str]
        :type exact_version: str
        :return:
        """
        cli = LinuxCLI(log_cmd=True)
        pkg_list = ' '.join(map(lambda v: v + (('=' + exact_version) if exact_version is not None else ''),
                                packages))
        print 'Uninstalling Debian packages: ' + pkg_list
        ret = cli.cmd('apt-get remove -y ' + pkg_list)

    def is_installed(self, package):
        cli = LinuxCLI()
        if not cli.grep_cmd('dpkg -l', package):
            return False
        return True

    def get_type(self):
        return "Debian"

