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
from TestScenario import TestScenario

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from TSM.TestCase import TestCase

from VTM.NeutronAPI import setup_neutron, clean_neutron
from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone


class NeutronTestCase(TestCase):
    main_network = None
    main_subnet = None
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
        cls.api = cls.vtm.get_client()
        cls.mn_api = create_midonet_client()

        setup_main_tunnel_zone(cls.mn_api,
                               {h.name: h.interfaces['eth0'].ip_list[0].ip
                                for h in cls.ptm.hypervisors.itervalues()},
                               cls.setup_logger)

        (cls.main_network, cls.main_subnet) = setup_neutron(cls.api,
                                                              subnet_cidr='10.0.1.1/24', log=cls.setup_logger)

    @classmethod
    def cleanup_neutron_test(cls):
        """
        Cleans up neutron database and restores it to a zero-state.  Can be overridden by
        subclasses to change behavior
        """
        clean_neutron(cls.api, log=cls.setup_logger)

    @classmethod
    def setUpClass(cls):
        super(NeutronTestCase, cls).setUpClass()
        cls.setup_neutron_test()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_neutron_test()
        super(NeutronTestCase, cls).tearDownClass()
