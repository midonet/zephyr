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
from common.CLI import LinuxCLI


class PluginComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo_obj, scheme, repo, username=None, password=None,
                         version=None, distribution='stable'):
        repo_name = repo + '-' + version.major + '-' + repo_obj.get_type()
        repo_obj.create_repo_file('midokura.networking-midonet', scheme, repo_name,
                                  username, password, distribution)
        LinuxCLI().cmd("apt-get install -y python3-software-properties")
        LinuxCLI().cmd("add-apt-repository -y cloud-archive:" + version.major)
        LinuxCLI().cmd("apt-get update")

    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        #TODO: Plugin's exact version is a little different from the version in the repo
        repo.install_packages(['python-neutron-plugin-midonet', 'python-neutron-lbaas',
                               'python-oslo-log'])

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.uninstall_packages(['python-neutron-plugin-midonet'])

    def is_installed(self, repo):
        return repo.is_installed(['python-neutron-plugin-midonet'])
