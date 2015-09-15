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

import platform

major_version_config_map = {
    '1': {
        # MEM-only
        'installed_packages': ['midolman', 'midonet-api', 'python-midonetclient'],
        'cmd_list_datapath': 'mm-dpctl --list-dps',
        'option_use_v2_stack': False,
        'option_api_uses_cluster': False,
        '7': {
            'option_config_mnconf': False
        },
        '8': {
            'option_config_mnconf': False
        },
        '9': {
            'option_config_mnconf': True
        }
    },

    '2015': {
        # OSS-only
        'installed_packages': ['midolman', 'midonet-api', 'python-midonetclient'],
        'cmd_list_datapath': 'mm-dpctl --list-dps',
        'option_use_v2_stack': False,
        'option_api_uses_cluster': False,
        '1': {
                'option_config_mnconf': False
        },
        '2': {
                'option_config_mnconf': False
        },
        '3': {
                'option_config_mnconf': True
        },
        '6': {
            'option_config_mnconf': True
        }
    },
    '5': {
        #MEM and OSS
        'installed_packages': ['midolman', 'python-midonetclient', 'midonet-cluster'],
        'cmd_list_datapath': 'mm-dpctl datapath --list',
        'option_use_v2_stack': True,
        'option_api_uses_cluster': True,
        '0': {
            'option_config_mnconf': True
        }
    },
}

LINUX_CENTOS = 1
LINUX_UBUNTU = 2

supported_linux_dist_map = { "Ubuntu": LINUX_UBUNTU, "centos": LINUX_CENTOS }

def get_linux_dist():
    dist, version, dist_id = platform.linux_distribution()
    if dist not in supported_linux_dist_map:
        raise ArgMismatchException('Unsupported Linux distribution: ' + dist)
    return supported_linux_dist_map[dist]

linux_dist = get_linux_dist()


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


def get_midolman_version():
    cli = LinuxCLI()

    if linux_dist == LINUX_UBUNTU:
        full_ver = cli.cmd('dpkg -l | grep -w midolman').split()[2].split('~')
        ver = full_ver[0]
        tag_ver = '' if len(full_ver) == 1 else full_ver[1]
    elif linux_dist == LINUX_CENTOS:
        ver = cli.cmd('yum info midolman | grep Version').split()[2]
        tag_ver = cli.cmd('yum info midolman | grep Release').split()[2]
    else:
        raise ArgMismatchException('Must run on Ubuntu or CentOS')

    return parse_midolman_version(ver, tag_ver)


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

#Midonet version
mn_version = get_midolman_version()

#Commands (as strings)
cmd_list_datapath = major_version_config_map[mn_version.major]['cmd_list_datapath']

#Options and switches
option_config_mnconf = major_version_config_map[mn_version.major][mn_version.minor]['option_config_mnconf']
option_use_v2_stack = major_version_config_map[mn_version.major]['option_use_v2_stack']
option_api_uses_cluster = major_version_config_map[mn_version.major]['option_api_uses_cluster']

#Global parameters
param_midonet_api_url = "http://localhost:" + ("8181" if option_api_uses_cluster else "8080") + "/midonet-api"