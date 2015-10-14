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

import importlib
import logging
import datetime

from common.Exceptions import *
from common.CLI import LinuxCLI
from TestScenario import TestScenario

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from TSM.TestCase import TestCase

from VTM.NeutronAPI import setup_neutron, clean_neutron
from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone
from VTM.Guest import Guest

import neutronclient.v2_0.client as neutron_client


class NeutronTestCase(TestCase):
    main_network = None
    main_subnet = None
    pub_network = None
    pub_subnet = None
    api = None
    """ :type: neutron_client.Client """
    mn_api = None

    def __init__(self, methodName='runTest'):
        super(NeutronTestCase, self).__init__(methodName)

    @classmethod
    def setup_neutron_test(cls):
        """
        Sets up neutron network and subnet.  Can be overridden by subclasses to change behavior
        """
        try:
            cls.api = cls.vtm.get_client()
            """ :type: neutron_client.Client """

            cls.mn_api = create_midonet_client()

            setup_main_tunnel_zone(cls.mn_api,
                                   {h.name: h.interfaces['eth0'].ip_list[0].ip
                                    for h in cls.ptm.hypervisors.itervalues()},
                                   cls.setup_logger)

            (cls.main_network, cls.main_subnet, cls.pub_network, cls.pub_subnet) = \
                setup_neutron(cls.api,
                              subnet_cidr='10.0.1.0/24',
                              pubsubnet_cidr='192.168.0.0/24',
                              log=cls.setup_logger)
        except Exception:
            cls.cleanup_neutron_test()
            raise

    @classmethod
    def cleanup_neutron_test(cls):
        """
        Cleans up neutron database and restores it to a zero-state.  Can be overridden by
        subclasses to change behavior
        """
        LinuxCLI(log_cmd=True).cmd('mysqldump --user=root --password=cat neutron > ' +
                                   cls.ptm.log_manager.root_dir + '/neutron.db.dump')
        clean_neutron(cls.api, log=cls.setup_logger)

    @classmethod
    def setUpClass(cls):
        super(NeutronTestCase, cls).setUpClass()
        cls.setup_neutron_test()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_neutron_test()
        super(NeutronTestCase, cls).tearDownClass()

    def cleanup_vms(self, vm_port_list):
        """
        :type vm_port_list: list[(Guest, port)]
        """
        for vm, port in vm_port_list:
            try:
                self.LOG.debug('Shutting down vm on port: ' + str(port))
                if vm is not None:
                    vm.stop_capture(on_iface='eth0')
                    if port is not None:
                        vm.unplug_vm(port['id'])
                if port is not None:
                    self.api.delete_port(port['id'])
            finally:
                if vm is not None:
                    vm.terminate()
