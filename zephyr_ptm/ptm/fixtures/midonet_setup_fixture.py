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

from zephyr.midonet import mn_api_utils
from zephyr_ptm.ptm.application.midolman import Midolman
from zephyr_ptm.ptm.config import version_config


class MidonetSetupFixture(object):
    def __init__(self, ptm_impl):
        """
        Sets up everything all tests will need to run Neutron.
        """
        super(MidonetSetupFixture, self).__init__()
        self.ptm_impl = ptm_impl
        self.LOG = None
        self.api = None

    def configure_logging(self, logger):
        self.LOG = logger
        if not self.LOG:
            self.LOG = logging.getLogger("neutron-setup-stdout")
            self.LOG.addHandler(logging.StreamHandler())

    def setup(self):
        self.api = mn_api_utils.create_midonet_client(
            version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url'))

        tunnel_zone_host_map = {}
        mm_name_list = []
        for _, host in self.ptm_impl.hosts_by_name.iteritems():
            # On each host, check if there is at least one
            # Midolman app running
            for app in host.applications:
                if isinstance(app, Midolman):
                    # If so, add the host and its eth0 interface
                    # to the tunnel zone map and move on to next host
                    for iface in host.interfaces.values():
                        if len(iface.ip_list) is not 0:
                            tunnel_zone_host_map[host.proxy_name] = (
                                iface.ip_list[0].ip)
                            break
                    mm_name_list.append(host.proxy_name)
                    break

        mn_api_utils.wait_for_all_mn_apps(
            self.api, mm_name_list, self.LOG, timeout=120)
        mn_api_utils.setup_main_tunnel_zone(
            self.api, tunnel_zone_host_map, self.LOG)

    def teardown(self):
        pass
