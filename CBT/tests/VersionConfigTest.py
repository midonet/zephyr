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

import unittest
import re
import CBT.VersionConfig as version_config

CFG_FILE='../../config/version_configuration.json'


class VersionConfigTest(unittest.TestCase):
    def test_version_map(self):
        self.assertFalse(version_config.ConfigMap.get_config_map(config_json=CFG_FILE)['1']['option_use_v2_stack'])

    def test_version_object(self):
        linux_dist = version_config.get_linux_dist()
        self.assertTrue(linux_dist == version_config.LINUX_CENTOS or
                        linux_dist == version_config.LINUX_UBUNTU)

        test_list = [(
                         ('2:5.0', '201509090010.2f5a1d9'),
                         version_config.Version('5', '0', '0', '201509090010.2f5a1d9', '2')),
                     (
                         ('05.02', '0.0.201509011045.80d8d50'),
                         version_config.Version('5', '2', '0', '201509011045.80d8d50')),
                     (
                         ('1.9.5', 'rc3'),
                         version_config.Version('1', '9', '5', 'rc3')),
                     (
                         ('5.0', '0.0.201509011045.80d8d50.el7'),
                         version_config.Version('5', '0', '0', '201509011045.80d8d50')),
                     (
                         ('1.8.9', '0.1.rc0.el7'),
                         version_config.Version('1', '8', '9', 'rc0')),
                     (
                         ('1.9.4', 'rc0'),
                         version_config.Version('1', '9', '4', 'rc0')),
                     (
                         ('2:1.9.4', 'rc0'),
                         version_config.Version('1', '9', '4', 'rc0', '2'))]

        for args, expected in test_list:
            mn_version = version_config.parse_midolman_version(*args)
            self.assertEqual(expected, mn_version)

    def test_version_strings(self):
        linux_dist = version_config.get_linux_dist()
        self.assertTrue(linux_dist == version_config.LINUX_CENTOS or
                        linux_dist == version_config.LINUX_UBUNTU)

        test_list = [
            (
                ('2:5.0', '201509090010.2f5a1d9'), '2:5.0.0-201509090010.2f5a1d9'
            ),
            (
                ('05.02', '0.0.201509011045.80d8d50'), '5.2.0-201509011045.80d8d50'
            ),
            (
                ('1.9.5', 'rc3'), '1.9.5-rc3'
            ),
            (
                ('5.0', '0.0.201509011045.80d8d50.el7'), '5.0.0-201509011045.80d8d50'
            ),
            (
                ('1.8.9', '0.1.rc0.el7'), '1.8.9-rc0'
            ),
            (
                ('1.9.4', 'rc0'), '1.9.4-rc0'
            )
        ]

        for args, expected in test_list:
            mn_version = version_config.parse_midolman_version(*args)
            self.assertEqual(expected, str(mn_version))

    def test_vars(self):
        print version_config.ConfigMap.get_configured_parameter('mn_version', config_json=CFG_FILE)
        print version_config.ConfigMap.get_configured_parameter('cmd_list_datapath', config_json=CFG_FILE)
        print version_config.ConfigMap.get_configured_parameter('option_config_mnconf', config_json=CFG_FILE)
        print version_config.ConfigMap.get_configured_parameter('option_use_v2_stack', config_json=CFG_FILE)
        print version_config.get_linux_dist()

from CBT.UnitTestRunner import run_unit_test
run_unit_test(VersionConfigTest)
