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

from collections import namedtuple
import logging

from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.utils import curl_delete
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.vtm.l2gw_fixture import L2GWFixture
from zephyr.vtm.neutron_api import get_neutron_api_url
from zephyr.vtm.neutron_api import NetData
from zephyr.vtm.neutron_api import RouterData

L2GWDevice = namedtuple("L2GWDevice", "gwdev l2gw l2conn")
L2GWSiteData = namedtuple("L2GWSiteData",
                          "tunnel_cidr tunnel_ip tunnel_gw tunnel_uplink_host "
                          "tunnel_uplink_iface az_cidr az_gw")
L2GWSiteTopo = namedtuple("L2GWSiteTopo",
                          "tunnel_port tunnel tunnel_ip vtep_router l2dev "
                          "az peer_router peer_router_port")
L2GWPeer = namedtuple("L2GWPeer", "rmac_entry gwdev_id fake_peer_port")
L2GWPeeredTopo = namedtuple("L2GWPeeredTopo", "east west")


class L2GWNeutronTestCase(NeutronTestCase):
    l2_setup = False

    @classmethod
    def _prepare_class(cls, vtm, test_case_logger=logging.getLogger()):
        super(L2GWNeutronTestCase, cls)._prepare_class(vtm,
                                                       test_case_logger)
        if not cls.l2_setup:
            L2GWFixture().setup()
            cls.l2_setup = True

    def create_ghost_port(self, az_net_id, ip, mac, other_port_id):
        ghost_port = self.create_port(
            "ghost_port", az_net_id, ip_addr=ip, mac=mac,
            device_owner="network:remote_site", port_security_enabled=False,
            device_id=other_port_id)
        self.LOG.debug("Created ghost port on east network mimicking "
                       "west-side router port: " + str(ghost_port))
        return ghost_port

    def hook_tenant_router_to_az_net(self, name, tenant_router_id, az_net_id,
                                     az_sub_id, az_gw):
        iface_port = self.create_port(name, az_net_id, ip_addr=az_gw,
                                      sub_id=az_sub_id,
                                      port_security_enabled=False)
        iface = self.create_router_interface(tenant_router_id,
                                             iface_port['id'])
        return iface_port, iface

    def hook_vtep_to_uplink_net(self, name, vtep_router_id, vtep_net_id,
                                tun_host, tun_iface, vtep_sub_id, tun_ip,
                                tun_gw):
        tun_port = self.create_port(
            name, vtep_net_id, host=tun_host,
            host_iface=tun_iface, sub_id=vtep_sub_id, ip_addr=tun_ip,
            port_security_enabled=False)
        vtep_tun_if = self.create_router_interface(vtep_router_id,
                                                   tun_port['id'])
        route = {'nexthop': tun_gw, 'destination': '0.0.0.0/0'}
        self.api.update_router(vtep_router_id, {'router': {'routes': [route]}})
        return tun_port, vtep_tun_if

    def create_router_peering_topo(self, name, az_cidr, az_gw, tun_cidr,
                                   tun_ip, tun_gw, tun_host, tun_iface,
                                   tenant_router_id, segment_id):
        vtep_net = self.create_network(name + "_VTEP_UPLINK", uplink=True)
        vtep_sub = self.create_subnet(name + "_VTEP_UPLINK", vtep_net['id'],
                                      tun_cidr, enable_dhcp=False)
        vtep_router = self.create_router(name + "_VTEP")
        (tun_port, vtep_tun_if) = self.hook_vtep_to_uplink_net(
            name, vtep_router['id'], vtep_net['id'], tun_host, tun_iface,
            vtep_sub['id'], tun_ip, tun_gw)

        gw = self.create_gateway_device(
            resource_id=vtep_router['id'],
            dev_type='router_vtep', tunnel_ip=tun_ip, name=name)
        l2gw = self.create_l2_gateway(name, gw['id'])
        az_net = self.create_network(name + "_AZ")
        az_sub = self.create_subnet(name + "_AZ", az_net['id'], az_cidr,
                                    enable_dhcp=False)
        l2gw_conn = self.create_l2_gateway_connection(
            az_net['id'], segment_id, l2gw['id'])
        (iface_port, iface) = self.hook_tenant_router_to_az_net(
            name, tenant_router_id, az_net['id'], az_sub['id'], az_gw)
        return {'vtep_net': vtep_net,
                'vtep_sub': vtep_sub,
                'vtep_router': vtep_router,
                'tun_port': tun_port,
                'vtep_tun_if': vtep_tun_if,
                'gateway_device': gw,
                'l2_gateway': l2gw,
                'l2_gateway_conn': l2gw_conn,
                'az_net': az_net,
                'az_sub': az_sub,
                'az_gw': az_gw,
                'az_iface_port': iface_port,
                'az_iface': iface}

    def add_peer(self, topo, tenant_router_id, segment_id, rmt_router_ip,
                 rmt_router_mac, rmt_private_cidr, dev_id, rmt_tunnel_ip,
                 add_route=True):
        route = {'nexthop': rmt_router_ip, 'destination': rmt_private_cidr}
        if add_route:
            self.api.update_router(tenant_router_id,
                                   {'router': {'routes': [route]}})
        ghost_port = self.create_ghost_port(
            topo['az_net']['id'], rmt_router_ip, rmt_router_mac,
            dev_id)
        rmac = self.create_remote_mac_entry(
            rmt_tunnel_ip, rmt_router_mac, segment_id,
            topo['gateway_device']['id'])

        topo = dict()
        topo['ghost_port'] = ghost_port
        topo['remote_mac_entry'] = rmac
        return topo
