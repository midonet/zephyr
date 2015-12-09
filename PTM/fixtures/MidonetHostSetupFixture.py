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

from PTM.fixtures.ServiceFixture import ServiceFixture

from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone
from PTM.application.Midolman import Midolman


class MidonetHostSetupFixture(ServiceFixture):
    def __init__(self, vtm, ptm, logger):
        """
        Sets up everything all tests will need to run Neutron.
        """
        super(MidonetHostSetupFixture, self).__init__()
        self.vtm = vtm
        self.ptm = ptm
        self.LOG = logger

        self.api = None

    def setup(self):
        try:
            self.api = create_midonet_client()

            tunnel_zone_host_map = {}
            for host_name, host in self.ptm.impl_.hosts_by_name.iteritems():
                # On each host, check if there is at least one Midolman app running
                for app in host.applications:
                    if isinstance(app, Midolman):
                        # If so, add the host and its eth0 interface to the tunnel zone map
                        # and move on to next host
                        tunnel_zone_host_map[host.name] = host.interfaces['eth0'].ip_list[0].ip
                        break

            setup_main_tunnel_zone(self.api,
                                   tunnel_zone_host_map,
                                   self.LOG)

        except Exception:
            self.teardown()
            raise

    def teardown(self):
        pass
