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

from common.CLI import LinuxCLI
from common.Exceptions import *

import json
import platform

LINUX_CENTOS = 1
LINUX_UBUNTU = 2

supported_linux_dist_map = { "Ubuntu": LINUX_UBUNTU, "centos": LINUX_CENTOS }


def get_linux_dist():
    dist, version, dist_id = platform.linux_distribution()
    if dist not in supported_linux_dist_map:
        raise ArgMismatchException('Unsupported Linux distribution: ' + dist)
    return supported_linux_dist_map[dist]


class Version(object):
    def __init__(self, major, minor='0', patch='0', tag=''):
        self.major = major
        """ :type: str"""
        self.minor = minor
        """ :type: str"""
        self.patch = patch
        """ :type: str"""
        self.tag = tag
        """ :type: str"""

    def __repr__(self):
        return self.major + '.' + self.minor + '.' + self.patch + '.' + self.tag

    def __eq__(self, other):
        return (other.major == self.major and
                other.minor == self.minor and
                other.patch == self.patch and
                other.tag == self.tag)


def parse_midolman_version(mnv, tag_ver):
    major_minor_patch = mnv.split(':')[-1].split('.')[0:3]

    tag_array = tag_ver.rstrip('.el7').rstrip('.el6').split('.')
    if len(tag_array) > 2:
        tag = '.'.join(tag_array[2:])
    else:
        tag = '.'.join(tag_array)

    def strip_zero(ver):
        return ver.lstrip('0') if ver != '0' else '0'

    return Version(*map(lambda ver: ver.lstrip('0') if ver != '0' else '0', major_minor_patch[0:3]), tag=tag)


def get_installed_midolman_version():
    cli = LinuxCLI()

    if get_linux_dist() == LINUX_UBUNTU:
        full_ver_str = cli.cmd('dpkg -l | grep -w midolman')
        if full_ver_str == "":
            raise ArgMismatchException('Midolman package not found.  Zephyr cannot run without Midolman.')

        full_ver = full_ver_str.split()[2].split('~')
        ver = full_ver[0]
        tag_ver = '' if len(full_ver) == 1 else full_ver[1]
    elif get_linux_dist() == LINUX_CENTOS:
        ver = cli.cmd('yum info midolman | grep Version').split()[2]
        tag_ver = cli.cmd('yum info midolman | grep Release').split()[2]
    else:
        raise ArgMismatchException('Must run on Ubuntu or CentOS')

    return parse_midolman_version(ver, tag_ver)


def get_config_map(config_json="config/version_configuration.json"):
    with open(config_json, "r") as f:
        major_version_config_map = json.load(f)
    return major_version_config_map


def get_configured_parameter(param, config_json="config/version_configuration.json"):
    mn_version = get_installed_midolman_version()

    major_version_config_map = get_config_map(config_json)
    if param == 'mn_version':
        return mn_version

    major_version_params = major_version_config_map[mn_version.major]
    minor_version_params = major_version_params[mn_version.minor]

    # Minor version config takes precedence and can override major version config
    if (param in minor_version_params):
        return minor_version_params[param]

    if (param in major_version_params):
        return major_version_params[param]

    raise ObjectNotFoundException("Param not found in either major or minor version config: " + param)
