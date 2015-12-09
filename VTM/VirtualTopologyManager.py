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

import logging

from common.Exceptions import *
from common.LogManager import LogManager
from VTM.Guest import Guest
from PTM.ptm_constants import PTM_LOG_FILE_NAME


class VirtualTopologyManager(object):
    def __init__(self,
                 physical_topology_manager,
                 client_api_impl=None,
                 log_manager=None):

        self.client_api_impl = client_api_impl
        self.physical_topology_manager = physical_topology_manager
        """ :type: PhysicalTopologyManager"""
        self.log_manager = log_manager if log_manager is not None else LogManager(root_dir='logs')
        """ :type: LogManager"""
        self.LOG = logging.getLogger('vtm-null-root')
        self.LOG.addHandler(logging.NullHandler())

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

    def get_client(self):
        return self.client_api_impl

    def create_vm(self, ip, mac=None, gw_ip=None, hv_host=None, name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param ip: str IP Address to use for the VM (required)
        :param hv_host: str: Hypervisor to use, otherwise the least-loaded HV host is chosen.
        :param name: str: Name to use for the VM.  Otherwise one is generated.
        :return: Guest
        """
        if self.physical_topology_manager is None:
            raise ArgMismatchException("Cannot create a VM without a PTM")
        new_vm = self.physical_topology_manager.create_vm(ip, mac, gw_ip, hv_host, name)
        if not new_vm:
            raise ObjectNotFoundException("VM not created: " + ip)

        return Guest(new_vm)
