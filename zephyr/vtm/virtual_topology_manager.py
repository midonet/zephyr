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
import logging

from zephyr.common import exceptions
from zephyr.common.log_manager import LogManager
from zephyr.common import utils
from zephyr.common import zephyr_constants
from zephyr.vtm.guest import Guest


class VirtualTopologyManager(object):
    def __init__(self,
                 client_api_impl=None,
                 log_manager=None):

        self.client_api_impl = client_api_impl
        self.log_manager = (log_manager
                            if log_manager is not None
                            else LogManager(root_dir='logs'))
        """ :type: LogManager"""
        self.LOG = logging.getLogger('vtm-null-root')
        self.LOG.addHandler(logging.NullHandler())
        self.log_level = logging.INFO
        self.debug = False
        self.underlay_system = None
        """
        :type: zephyr.vtm.underlay.underlay_system.UnderlaySystem
        """

    def configure_logging(
            self, log_name='vtm-root',
            debug=False,
            log_file_name=zephyr_constants.ZEPHYR_LOG_FILE_NAME):
        self.log_level = (logging.DEBUG
                          if debug is True
                          else logging.INFO)
        self.debug = debug

        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(
                file_name=log_file_name,
                name=log_name + '-debug',
                file_log_level=self.log_level,
                stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(
                file_name=log_file_name,
                name=log_name,
                log_level=self.log_level)

    def get_client(self):
        return self.client_api_impl

    def get_host(self, name):
        return self.underlay_system.hosts.get(name, None)

    def create_vm(self, ip_addr, mac=None,
                  gw_ip=None, hv_host=None, name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param ip_addr: str IP Address to use for the VM (required)
        :param mac: str Ether Address to use for the VM
        :param gw_ip: str Gateway IP to use for the VM
        :param hv_host: str: Hypervisor to use, otherwise the least-loaded HV
        host is chosen.
        :param name: str: Name to use for the VM.  Otherwise one is generated.
        :return: Guest
        """
        if not self.underlay_system:
            raise exceptions.ArgMismatchException(
                "Can't create VM without an underlay system")
        vm_underlay = self.underlay_system.create_vm(
            ip_addr=ip_addr, mac=mac,
            gw_ip=gw_ip, hv_host=hv_host, name=name)
        return Guest(vm_underlay=vm_underlay)

    def read_underlay_config(
            self,
            config_json=zephyr_constants.DEFAULT_UNDERLAY_CONFIG):
        """
        All underlay configs MUST name a 'underlay_system' class, which
        will be used to select which type of underlay to use for zephyr.
        The read config will then be delegated to that class, which will
        read the subsequent specific configuration for that underlay type.
        """
        self.LOG.info('Loading underlay config from: ' + config_json)

        with open(config_json, 'r') as cfg:
            config_map = json.load(cfg)

        und_sys_pkg = 'zephyr.vtm.underlay.direct_underlay_system'
        und_sys_class = und_sys_pkg + '.DirectUnderlaySystem'

        if 'underlay_system' in config_map:
            und_sys_class = config_map['underlay_system']
        self.underlay_system = utils.get_class_from_fqn(und_sys_class)(
            debug=self.debug,
            logger=self.LOG)

        """ :type: zephyr.vtm.underlay.underlay_system.UnderlaySystem"""
        self.underlay_system.read_config(config_map)
