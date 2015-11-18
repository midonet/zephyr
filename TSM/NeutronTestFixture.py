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

from TSM.TestFixture import TestFixture

from common.Exceptions import *
from common.CLI import LinuxCLI

from VTM.NeutronAPI import setup_neutron, clean_neutron
from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone


class NeutronTestFixture(TestFixture):
    def __init__(self, vtm, ptm, logger):
        """
        Sets up everything all tests will need to run Neutron.
        """
        super(NeutronTestFixture, self).__init__()
        self.vtm = vtm
        self.ptm = ptm
        self.LOG = logger

        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet = None
        self.api = None
        self.mn_api = None

    def setup(self):
        try:
            self.api = self.vtm.get_client()
            """ :type: neutron_client.Client """

            self.mn_api = create_midonet_client()

            setup_main_tunnel_zone(self.mn_api,
                                   {h.name: h.interfaces['eth0'].ip_list[0].ip
                                    for h in self.ptm.hypervisors.itervalues()},
                                   self.LOG)

            (self.main_network, self.main_subnet, self.pub_network, self.pub_subnet) = \
                setup_neutron(self.api,
                              subnet_cidr='10.0.1.0/24',
                              pubsubnet_cidr='192.168.0.0/24',
                              log=self.LOG)
        except Exception:
            self.teardown()
            raise

    def teardown(self):
        """
        Cleans up neutron database and restores it to a zero-state.  Can be overridden by
        subclasses to change behavior
        """
        LinuxCLI(log_cmd=True).cmd('mysqldump --user=root --password=cat neutron > ' +
                                   self.ptm.log_manager.root_dir + '/neutron.db.dump')
        clean_neutron(self.api, log=self.LOG)
