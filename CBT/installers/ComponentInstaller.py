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

    def create_repo_file(self, repo_obj, scheme, repo, username=None, password=None,
                         version=None, distribution='stable'):
        """
        Creates an entry in the repo file given the parameters, which can access and install
        the component.
        :type repo_obj: PackageRepo
        :type scheme: str
        :type repo: str
        :type username: str
        :type password: str
        :type version: Version
        :type distribution: str
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
