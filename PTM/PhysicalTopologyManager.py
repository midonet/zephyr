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

from MNRootServer import MNRootServer
from MapConfigReader import MapConfigReader
from PhysicalTopologyConfig import PhysicalTopologyConfig

from common.Exceptions import *
from common.CLI import LinuxCLI
from common.LogManager import LogManager

import logging
import json

class PhysicalTopologyManager(object):
    def __init__(self, log_root_dir='/var/log/zephyr/ptm'):
        super(PhysicalTopologyManager, self).__init__()
        self.log_root_dir = log_root_dir
        """ :type: str"""
        self.root_servers = {}
        """ :type: dict [str, RootServer]"""
        self.log_manager = LogManager()
        """ :type: LogManager"""

        if not LinuxCLI().exists(self.log_root_dir):
            LinuxCLI(priv=False).mkdir(self.log_root_dir)

        self.logger = self.log_manager.add_tee_logger(self.log_root_dir + '/ptm-output.txt', name='ptm-root',
                                                      file_overwrite=True, file_log_level=logging.DEBUG)

    def add_root_server(self, name, root_server):
        if name in self.root_servers:
            raise ObjectAlreadyAddedException('Root server: ' + name + ' already added to PTM')
        root_server.set_log_manager(self.log_manager)
        self.root_servers[name] = root_server

    def startup(self):
        for name, rs in self.root_servers.iteritems():
            rs.startup()

    def config_mn_from_file(self, file_name='config.json'):
        with open(file_name, 'r') as f:
            config_obj = json.load(f)

        os_host = MNRootServer('root', self.log_root_dir + '/root')
        config = MapConfigReader.get_physical_topology_config(config_obj)
        os_host.config_from_physical_topology_config(config)
        self.add_root_server(os_host.name, os_host)
        os_host.init()
        return os_host
