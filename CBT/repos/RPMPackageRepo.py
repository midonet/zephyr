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

from CBT.repos.PackageRepo import PackageRepo
from common.CLI import LinuxCLI


class RPMPackageRepo(PackageRepo):
    def create_repo_file(self, component, repo_scheme, repo_dir,
                         repo_user=None, repo_pass=None,
                         repo_distro='nightly', repo_component=''):
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

    def get_type(self):
        return "rpm"

