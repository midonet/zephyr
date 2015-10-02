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

from CBT.installers.ComponentInstaller import ComponentInstaller


class MidonetUtilsComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo, scheme, server, main_dir, username=None, password=None,
                         version=None, distribution='stable'):
        sub_dir = 'thirdparty'
        repo.create_repo_file('midonet-3rdparty', scheme, server, main_dir, username, password, sub_dir)


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
