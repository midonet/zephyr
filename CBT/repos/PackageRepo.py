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
    def __init__(self, repo_server, curl_server):
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
        self.repo_server = repo_server
        self.curl_server = curl_server

    def create_repo_file(self, component, repo_scheme, repo_dir,
                         repo_user=None, repo_pass=None,
                         repo_distro='nightly', repo_component=''):
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


    def get_type(self):
        """
        Returns the type of the Repo as a string.  Users of the repos can check this string,
        if there are special actions to take for one repo type versus another, for example.
        :return: str
        """
        return "Unknown"




