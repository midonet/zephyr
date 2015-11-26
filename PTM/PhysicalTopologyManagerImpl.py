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

import logging

from common.LogManager import LogManager
from PTM.ptm_constants import PTM_LOG_FILE_NAME


class PhysicalTopologyManagerImpl(object):
    """
    Manage physical topology for test.
    :type root_dir: str
    :type log_manager: LogManager
    """
    def __init__(self, root_dir='.', log_manager=None):
        super(PhysicalTopologyManagerImpl, self).__init__()
        self.log_manager = log_manager if log_manager is not None else LogManager(root_dir="logs")
        """ :type: LogManager"""
        self.root_dir = root_dir
        self.LOG = logging.getLogger('ptm-null-root')
        self.LOG.addHandler(logging.NullHandler())
        self.CONSOLE = logging.getLogger('ptm-null-console')
        self.CONSOLE.addHandler(logging.NullHandler())
        self.log_level = logging.INFO
        self.debug = False

    def configure_logging(self, log_name='ptm-root', debug=False, log_file_name=PTM_LOG_FILE_NAME):
        self.log_level = logging.DEBUG if debug is True else logging.INFO
        self.debug = debug

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(file_name=log_file_name,
                                                       name=log_name + '-debug',
                                                       file_log_level=self.log_level,
                                                       stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(file_name=log_file_name,
                                                        name=log_name,
                                                        log_level=self.log_level)

        self.CONSOLE = self.log_manager.add_stdout_logger(name=log_name + '-console', log_level=logging.INFO)

    def configure(self, config_file, file_type='json'):
        """
        Configure the PTM with information from the given JSON file.

        IMPORTANT NOTE!!!  For Hosts and for Applications, the implementation class name
        in the [implementation] section MUST have the class's name be the same name as the
        last dotted-name in the module (the string after the last dot (.), without the
        .py extension)!

        :type file_name: str
        :return:
        """
        pass

    def print_config(self, indent=0, logger=None):
        pass

    def startup(self):
        pass

    def shutdown(self):
        pass

    def ptm_host_app_control(self, app_cmd, host_json, app_json, arg_list):
        pass

    def create_vm(self, ip, gw_ip=None, requested_hv_host=None, requested_vm_name=None):
        pass
