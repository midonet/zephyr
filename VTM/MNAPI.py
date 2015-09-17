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

from midonetclient.api import MidonetApi
from midonetclient.tunnel_zone import TunnelZone
from midonetclient.bridge import Bridge

from common.Exceptions import *
import CBT.VersionConfig as version_config

def create_midonet_client(base_uri=version_config.ConfigMap.get_configured_parameter('param_midonet_api_url'),
                          username=None, password=None, project_id=None):
   return MidonetApi(base_uri, username, password, project_id)


def setup_main_tunnel_zone(api, host_ip_map, logger=None):
    """
    Setup main tunnel zone for Midonet API.  The host-IP map should be a
    map of host key to an IP string.
    :type api: MidonetAPI
    :type host_ip_map: dict [str, str]
    :type logger: logging.Logger
    :return:
    """
    if not isinstance(api, MidonetApi):
        raise ArgMismatchException('Need midonet client for this test')

    if logger is None:
        logger = logging.getLogger()
        logger.addHandler(logging.NullHandler())

    tzs = api.get_tunnel_zones()
    """:type: list[TunnelZone]"""

    # If main tunnel zone already found, don't re-add
    for tz in tzs:
       if tz.get_name() == "main":
           return

    logger.info('Setting up VTM main tunnel zone')
    tz = api.add_gre_tunnel_zone().name('main').create()

    # Add all hosts/interface tuples to the tunnel zone
    for h in api.get_hosts(query={}):
        logger.info("MN API Host name: " + h.get_name() + ", id: " + h.get_id())

        if h.get_name() not in host_ip_map:
            raise ArgMismatchException('MN Host: ' + h.get_name() + ' has no configured IPs listed!')

        tzh = tz.add_tunnel_zone_host()
        tzh.ip_address(host_ip_map[h.get_name()])
        tzh.host_id(h.get_id())
        tzh.create()

    return tz


def setup_main_bridge(api):

    if not isinstance(api, MidonetApi):
        raise ArgMismatchException('Need midonet client for this test')

    brs = api.get_bridges(None)
    """:type: list[Bridge]"""

    for br in brs:
        if br.get_name() == "bridge_0":
            return br

    return api.add_bridge().name('bridge_0').tenant_id('test1').create()

