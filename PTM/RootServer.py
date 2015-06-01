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

from common.Exceptions import *
from common.CLI import LinuxCLI, NetNSCLI, CREATENSCMD, REMOVENSCMD
from common.LogManager import LogManager
from Host import Host

import logging

class RootServer(Host):
    def __init__(self, name='root', log_root_dir='/tmp/zephyr/root'):
        super(RootServer, self).__init__('root', LinuxCLI(), lambda name: None, lambda name: None, self)
        self.log_manager = None
        """ :type: common.LogManager"""
        self.root_logger = None
        """ :type: logging.Logger"""
        self.log_root_dir = log_root_dir
        """ :type: str"""
        self.name = name
        """ :type: str"""

    def set_log_manager(self, log_manager):
        """
        Sets the Root Server's log manager
        :type log_manager: LogManager
        :return:
        """
        self.log_manager = log_manager
        self.root_logger = self.log_manager.add_tee_logger(self.log_root_dir + '/')

    @staticmethod
    def create_from_physical_topology_config(ptc):
        pass

    def print_config(self, indent=0):
        pass

    def init(self):
        pass

    def create_hosts(self):
        pass

    def remove_hosts(self):
        pass

    def prepare_files(self):
        pass

    def add_interfaces(self):
        pass

    def delete_interfaces(self):
        pass

    def start_host_process(self):
        pass

    def stop_host_process(self):
        pass

    def startup(self):
        pass

    def shutdown(self):
        pass

    def control(self, *args, **kwargs):
        pass