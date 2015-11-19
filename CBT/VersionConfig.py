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
import os

LINUX_CENTOS = 1
LINUX_UBUNTU = 2

supported_linux_dist_map = {"Ubuntu": LINUX_UBUNTU, "centos": LINUX_CENTOS}


def get_linux_dist():
    dist, version, dist_id = platform.linux_distribution()
    if dist not in supported_linux_dist_map:
        raise ArgMismatchException('Unsupported Linux distribution: ' + dist)
    return supported_linux_dist_map[dist]


class Version(object):
    def __init__(self, major, minor='0', patch='0', tag='', epoch=''):
        self.major = major
        """ :type: str"""
        self.minor = minor
        """ :type: str"""
        self.patch = patch
        """ :type: str"""
        self.tag = tag
        """ :type: str"""
        self.epoch = epoch
        """ :type: str"""

    def __repr__(self):
        ret = ''
        if self.epoch != '':
            ret += self.epoch + ":"
        ret += self.major
        if self.minor != '':
            ret += '.' + self.minor
        if self.patch != '':
            ret += '.' + self.patch
        if self.tag != '':
            ret += '-' + self.tag

        return ret

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other

        return (other.epoch == self.epoch and
                other.major == self.major and
                other.minor == self.minor and
                other.patch == self.patch and
                other.tag == self.tag)


def parse_midolman_version(mnv, tag_ver=''):
    epoch_version = mnv.split(':', 2)

    epoch = ''
    if len(epoch_version) > 1:
        epoch = epoch_version[0]

    major_minor_patch = epoch_version[-1].split('.')[0:3]

    tag_array = tag_ver.rstrip('.el7').rstrip('.el6').split('.')
    if len(tag_array) > 2:
        tag = '.'.join(tag_array[2:])
    else:
        tag = '.'.join(tag_array)

    return Version(*map(lambda ver: ver.lstrip('0') if ver != '0' else '0', major_minor_patch[0:3]),
                   tag=tag, epoch=epoch)


def get_installed_midolman_version():
    cli = LinuxCLI()

    if get_linux_dist() == LINUX_UBUNTU:
        full_ver_str = cli.cmd('dpkg -l | grep -w midolman').stdout
        if full_ver_str == "":
            raise ArgMismatchException('Midolman package not found.  Zephyr cannot run without Midolman.')

        full_ver = full_ver_str.split()[2].split('~')
        ver = full_ver[0]
        tag_ver = '' if len(full_ver) == 1 else full_ver[1]
    elif get_linux_dist() == LINUX_CENTOS:
        ver = cli.cmd('yum info midolman | grep Version').stdout.split()[2]
        tag_ver = cli.cmd('yum info midolman | grep Release').stdout.split()[2]
    else:
        raise ArgMismatchException('Must run on Ubuntu or CentOS')

    return parse_midolman_version(ver, tag_ver)


class ConfigMap(object):

    major_version_config_map = None

    @classmethod
    def get_config_map(cls,
                       config_json=os.path.dirname(os.path.realpath(__file__)) +
                                   '/../config/midonet_version_configuration.json'):


        with open(config_json, "r") as f:
            cls.major_version_config_map = json.load(f)
        return cls.major_version_config_map

    @classmethod
    def get_configured_parameter(cls, param, version=None,
                                 config_json=os.path.dirname(os.path.realpath(__file__)) +
                                             '/../config/midonet_version_configuration.json'):
        """
        Retrieve a parameter based on the actively installed verison of Midolman.  If Midolman
        is not installed, do not use this function as it will throw an exception.  Instead, get
        the map manually and check the keys with the 'get_config_map' function.
        :type param: str
        :type config_json: str
        :return:
        """
        mn_version = get_installed_midolman_version() if version is None else version

        if cls.major_version_config_map is None:
            cls.major_version_config_map = cls.get_config_map(config_json)

        if param == 'mn_version':
            return mn_version

        if mn_version.major not in cls.major_version_config_map:
            raise ObjectNotFoundException('No version configuration found for major version: ' +
                                          str(mn_version.major))

        major_version_params = cls.major_version_config_map[mn_version.major]

        # Only use minor params, if it is present, otherwise assume major params will
        # work for unlisted minor versions
        minor_version_params = None
        if mn_version.minor in major_version_params:
            minor_version_params = major_version_params[mn_version.minor]

        # Minor version config takes precedence and can override major version config
        if minor_version_params and param in minor_version_params:
            return minor_version_params[param]

        if param in major_version_params:
            return major_version_params[param]

        raise ObjectNotFoundException("Param not found in either major or minor version config: " + param)
