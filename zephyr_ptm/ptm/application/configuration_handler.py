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

from zephyr.common.cli import LinuxCLI


# TODO(micucci): Clean up how the configs are created and transformed
class ConfigurationHandler(object):
    def __init__(self):
        super(ConfigurationHandler, self).__init__()

    def configure(self, **kwargs):
        pass


class FileConfigurationHandler(ConfigurationHandler):
    def __init__(self):
        super(FileConfigurationHandler, self).__init__()
        self.cli = LinuxCLI()

    def mount_config(self, **kwargs):
        pass

    def unmount_config(self, **kwargs):
        pass


class ProgramConfigurationHandler(ConfigurationHandler):
    def __init__(self):
        super(ProgramConfigurationHandler, self).__init__()
        self.cli = LinuxCLI()
