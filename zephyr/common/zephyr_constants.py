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

import json
import os

ZEPHYR_LOG_FILE_NAME = 'zephyr-output.log'
DEFAULT_UNDERLAY_CONFIG = 'underlay-config.json'


class ZephyrInit(object):
    BIN_ROOT_DIR = '.'
    CONF_ROOT_DIR = '.'

    CONFIG_FILE = 'zephyr.conf'

    @classmethod
    def init(cls, config_file=None):
        if not config_file:
            config_file = cls.CONFIG_FILE

        with open(config_file, "r") as f:
            config = json.load(f)

        if 'bin_dir' not in config:
            raise ValueError("bin_dir not found in config")

        if 'config_dir' not in config:
            raise ValueError("config_dir not found in config")

        cls.BIN_ROOT_DIR = os.path.abspath(config['bin_dir'])
        cls.CONF_ROOT_DIR = os.path.abspath(config['config_dir'])


DEFAULT_ECHO_PORT = 5080
