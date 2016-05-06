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

import datetime
import logging
from zephyr_ptm.ptm import ptm_constants


class Application(object):
    @staticmethod
    def get_name():
        return '<unknown>'

    def __init__(self, host, app_id=''):
        """
        :type host: Host
        :type app_id: str
        :return:
        """
        self.host = host
        """ :type: Host"""
        self.cli = host.cli
        """ :type: LinuxCLI"""

        self.log_manager = self.host.log_manager
        self.LOG = logging.getLogger('ptm-null-root')
        """ :type: logging.Logger"""
        self.name = self.get_name()
        self.debug = False
        """ :type bool"""
        self.log_level = logging.INFO
        self.unique_id = app_id
        self.log_file_name = ptm_constants.ZEPHYR_LOG_FILE_NAME

    def configure(self, host_cfg, app_config):
        pass

    def configure_logging(self,
                          log_file_name, debug=False):
        self.log_level = logging.DEBUG if debug is True else logging.INFO
        self.debug = debug
        self.log_file_name = log_file_name
        msec = int(datetime.datetime.utcnow().microsecond / 1000)
        logname = (self.name + '.' +
                   datetime.datetime.utcnow().strftime('%H%M%S') +
                   '.' + str(msec))

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(
                file_name=log_file_name,
                name=logname + '-debug',
                file_log_level=self.log_level,
                stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(
                file_name=log_file_name,
                name=logname,
                log_level=self.log_level)

    def print_config(self, indent=0):
        print(('    ' * indent) + self.name + ': Impl class ' +
              self.__class__.__name__)
        print(('    ' * (indent + 1)) + 'UUID: ' + str(self.unique_id))

    def prepare_config(self, log_manager):
        pass

    def create_cfg_map(self):
        return {}

    def create_app_cfg_map_for_process_control(self):
        ret = {
            'log_file_name': self.log_file_name,
            'class': self.__module__ + "." + self.__class__.__name__}
        ret.update(self.create_cfg_map())
        return ret

    def config_app_for_process_control(self, cfg_map):
        pass

    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def control_start(self):
        pass

    def control_stop(self):
        pass

    def prepare_environment(self):
        pass

    def cleanup_environment(self):
        pass
