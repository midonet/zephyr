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

from installers.MidonetComponentInstaller import MidonetComponentInstaller
from installers.MidonetUtilsComponentInstaller import MidonetUtilsComponentInstaller
from installers.PluginComponentInstaller import PluginComponentInstaller
from installers.NeutronComponentInstaller import NeutronComponentInstaller

from repos.DebianPackageRepo import DebianPackageRepo
from repos.RPMPackageRepo import RPMPackageRepo

from common.Exceptions import *

import VersionConfig as version_config


url_scheme = "http://"
artifactory_server = "artifactory.bcn.midokura.com/artifactory"
curl_server = "http://artifactory.bcn.midokura.com/artifactory/api/gpg/key/public"

install_config = {
    'midonet':
        {
            'repo': 'midonet',
            'scheme': 'http',
            'installer': MidonetComponentInstaller,
            'deps': [],
        },
    'midonet-mem':
        {
            'repo': 'mem',
            'scheme': 'http',
            'installer': MidonetComponentInstaller,
            'deps': [],
        },
    'midonet-utils':
        {
            'repo': 'misc',
            'scheme': 'http',
            'installer': MidonetUtilsComponentInstaller,
            'deps': [],
        },
    'plugin':
        {
            'repo': 'openstack',
            'scheme': 'http',
            'installer': PluginComponentInstaller,
            'deps': ['python-midonetclient'],
        },
    'neutron':
        {
            'repo': '',
            'scheme': 'http',
            'installer': NeutronComponentInstaller,
            'deps': [],
        }
}


def get_os_repo(server=artifactory_server):
    """
    Returns a proper repo for the given parameters and the base OS (debian, rpm, etc.)
    :return: PackageRepo
    """
    if version_config.get_linux_dist() == version_config.LINUX_CENTOS:
        repo = RPMPackageRepo(server, curl_server)
    elif version_config.get_linux_dist() == version_config.LINUX_UBUNTU:
        repo = DebianPackageRepo(server, curl_server)
    else:
        raise ArgMismatchException("Only supported on CentOS or Ubuntu")
    return repo


def get_config_info(component, version):
    if component not in install_config:
        raise ArgMismatchException('Component has no defined install process: ' + component)

    class_type = install_config[component]['installer']
    """ :type: type"""

    installer_obj = class_type(version)
    """ :type: ComponentInstaller"""

    scheme = install_config[component]['scheme']
    """ :type: str"""

    repo = install_config[component]['repo']
    """ :type: str"""

    deps = install_config[component]['deps']
    """ :type: list[str]"""

    return (installer_obj, scheme, repo, deps)


def install_component(component='midonet',
                      server=artifactory_server, username=None, password=None,
                      version=None, distribution='stable',
                      exact_version=None):
    """
    :type repo: PackageRepo
    :type component: string
    :type version: Version
    """
    cfg_tuple = get_config_info(component, version)
    installer = cfg_tuple[0]
    repo_obj = get_os_repo(server)
    installer.create_repo_file(repo_obj, cfg_tuple[1], cfg_tuple[2], username, password, version, distribution)

    dep_list = cfg_tuple[3]
    for dep in dep_list:
        print "Checking dependency: " + dep
        if not repo_obj.is_installed(dep):
            raise ObjectNotFoundException('Dependent package must be installed first: ' + dep)

    installer.install_packages(repo_obj, exact_version=exact_version)


def uninstall_component(component='midolman',
                        server=artifactory_server, username='', password='',
                        version=None, distribution='stable',
                        exact_version=None):
    """
    :type repo: PackageRepo
    :type component: string
    :type version: Version
    """
    cfg_tuple = get_config_info(component, version)
    repo = get_os_repo(server)

    cfg_tuple[0].uninstall_packages(repo, exact_version=exact_version)
