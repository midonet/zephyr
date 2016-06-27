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

    def setup_peer_l2gw(self, tun_cidr, tun_ip, tun_gw, tun_host, tun_iface,
                        az_cidr, az_gw, segment_id, peer_router, peer_name):
        tun_network = None
        tun_subnet = None
        vtep_router = None
        vtep_tun_if = None
        gwdev_id = None
        l2gw_id = None
        l2conn_id = None
        az_net = None
        az_sub = None
        peer_router_iface = None

        try:
            # Set up peer **********************************
            # Create the Neutron router that will be peered
            # Create an uplink network (Midonet-specific extension used for
            # provider:network_type)
            tun_network = self.create_network(peer_name, uplink=True)
            tun_subnet = self.create_subnet(peer_name, tun_network['id'],
                                            tun_cidr, enable_dhcp=False)

            # Create VTEP router
            vtep_router = self.create_router(peer_name)

            # Create "port" on router by creating a port on the
            # special uplink network bound to the physical interface on
            # the physical host, and then linking that network port to
            # the router's interface.
            tun_port = self.create_uplink_port(peer_name, tun_network['id'],
                                               tun_host, tun_iface,
                                               tun_subnet['id'], tun_ip)

            # Bind port to edge router
            vtep_tun_if = self.api.add_interface_router(
                vtep_router['id'], {'port_id': tun_port['id']})

            self.LOG.info('Added interface to ' + peer_name +
                          ' VTEP router: ' + str(vtep_tun_if))

            # Set up GW device
            gw = self.create_gateway_device(
                resource_id=vtep_router['id'],
                dev_type='router_vtep', tunnel_ip=tun_ip, name=peer_name)
            gwdev_id = gw['id']

            # Set up L2GW
            l2gw = self.create_l2_gateway(peer_name, gwdev_id)
            l2gw_id = l2gw['id']

            # Set up shared (Availability Zone) subnet
            az_net = self.api.create_network(
                {'network': {'name': 'az_net_' + peer_name,
                             'tenant_id': 'admin'}})['network']

            az_sub = self.api.create_subnet(
                {'subnet': {'name': 'az_sub_' + peer_name,
                            'tenant_id': 'admin',
                            'network_id': az_net['id'],
                            'enable_dhcp': False,
                            'gateway_ip': None,
                            'ip_version': 4,
                            'cidr': az_cidr}})['subnet']

            # Set up l2gw connection from VTEP to shared subnet
            l2gw_conn = self.create_l2_gateway_connection(
                az_net['id'], segment_id, l2gw_id)
            l2conn_id = l2gw_conn['id']

            # Set up tenant router port on the shared subnet
            peer_router_port = self.api.create_port(
                {'port':
                    {'name': 'tenant_port_' + peer_name,
                     'network_id': az_net['id'],
                     'admin_state_up': True,
                     'fixed_ips': [{'subnet_id': az_sub['id'],
                                    'ip_address': az_gw}],
                     'tenant_id': 'admin'}})['port']
            self.LOG.debug('Created port for peer router on AZ ' +
                           peer_name + ' network: ' + str(peer_router_port))
            # Add the shared subnet port to the tenant router
            peer_router_iface = self.api.add_interface_router(
                peer_router['id'], {'port_id': peer_router_port['id']})

            # Add the default route through the tunnel uplink
            vtep_router = self.api.update_router(
                vtep_router['id'],
                {'router': {
                    'routes': [{'nexthop': tun_gw,
                                'destination': '0.0.0.0/0'}]}})['router']

            self.LOG.debug(peer_name + ' peer finished: ' + str(peer_router))

            return L2GWSiteTopo(
                tunnel_port=tun_port,
                tunnel=NetData(network=tun_network, subnet=tun_subnet),
                tunnel_ip=tun_ip,
                vtep_router=RouterData(router=vtep_router,
                                       if_list=[vtep_tun_if]),
                l2dev=L2GWDevice(gwdev=gwdev_id, l2gw=l2gw_id,
                                 l2conn=l2conn_id),
                az=NetData(network=az_net, subnet=az_sub),
                peer_router=RouterData(router=peer_router,
                                       if_list=[peer_router_iface]),
                peer_router_port=peer_router_port)

        except Exception as e:
            self.LOG.fatal("Error creating shared-site topology: " + str(e))
            self.clean_peer_data(
                tunnel=NetData(network=tun_network, subnet=tun_subnet),
                vtep_router=RouterData(
                    router=vtep_router, if_list=[vtep_tun_if]),
                l2dev=L2GWDevice(gwdev=gwdev_id, l2gw=l2gw_id,
                                 l2conn=l2conn_id),
                az=NetData(network=az_net, subnet=az_sub),
                peer_router=RouterData(router=peer_router,
                                       if_list=[peer_router_iface]))
            return None

    def peer_sites(self,
                   east, east_private_cidr,
                   west, west_private_cidr, segment_id):
        """
        Peer an east and west topology (must have already been setup
        with setup_peer_l2gw())
        :type east: L2GWSiteTopo
        :type east_private_cidr: str
        :type west: L2GWSiteTopo
        :type west_private_cidr: str
        :param segment_id: str
        :return:
        """
        east_peer = None
        west_peer = None
        try:
            east_peer = self.peer_sites_side(east, west,
                                             west_private_cidr, segment_id)
            west_peer = self.peer_sites_side(west, east,
                                             east_private_cidr, segment_id)
            return L2GWPeeredTopo(east_peer, west_peer)
        except Exception as e:
            if east_peer:
                self.clean_peered_site_data(east_peer)
            if west_peer:
                self.clean_peered_site_data(west_peer)
            self.LOG.fatal("Error peering L2GW topologies: " + str(e))
            return None

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

    def peer_sites_side(self, near_side, far_side,
                        far_private_cidr, segment_id):
        """
        Peer an east and west topology (must have already been setup
        with setup_peer_l2gw())
        :type near_side: L2GWSiteTopo
        :type far_side: L2GWSiteTopo
        :type far_private_cidr: str
        :type segment_id: str
        :return:
        """
        rmac_entry = None
        fake_peer_port = None

        if not near_side or not far_side:
            raise ObjectNotFoundException("Need both near and far sites "
                                          "to be valid")

        try:
            # Unified set up ************************************************
            # Add the route to the east side private subnet through the
            # west side gateway on the shared subnet
            far_port = far_side.peer_router_port
            far_port_ip_list = far_port['fixed_ips']
            far_port_main_ip_struct = far_port_ip_list[0]
            far_port_main_ip = far_port_main_ip_struct['ip_address']
            self.api.update_router(
                near_side.peer_router.router['id'],
                {'router': {'routes': [{'nexthop': far_port_main_ip,
                                        'destination': far_private_cidr}]}})

            # Create ghost ports on both networks for each others' peer ports
            fake_peer_port = self.create_ghost_port(
                near_side.az.network['id'], far_port_main_ip,
                far_port['mac_address'], far_port['id'])

            # Add MAC addresses into each site to tunnel to far end
            rmac = self.create_remote_mac_entry(
                far_side.tunnel_ip, far_side.peer_router_port['mac_address'],
                segment_id, near_side.l2dev.gwdev)

            rmac_entry = rmac['id']

            return L2GWPeer(rmac_entry,
                            near_side.l2dev.gwdev,
                            fake_peer_port)
        except Exception as e:
            self.clean_peered_site_data(L2GWPeer(rmac_entry,
                                                 near_side.l2dev.gwdev,
                                                 fake_peer_port))
            self.LOG.fatal("Error peering L2GW topologies: " + str(e))
            return None

    def clean_peered_site(self, topo):
        """
        :type topo: L2GWPeeredTopo
        """
        if topo:
            self.clean_peered_site_data(topo.east)
            self.clean_peered_site_data(topo.west)

    def clean_peered_site_data(self, peer_site):
        curl_url = get_neutron_api_url(self.api)
        try:
            if peer_site:
                if peer_site.rmac_entry:
                    self.delete_remote_mac_entry(peer_site.gwdev_id,
                                                 peer_site.rmac_entry)
                    self.LOG.debug("Cleaning RMAC entry: " + curl_url)
                if peer_site.fake_peer_port:
                    self.LOG.debug("Clearing ghost port: " +
                                   peer_site.fake_peer_port['id'])
                    self.api.delete_port(peer_site.fake_peer_port['id'])

        except Exception as e:
            self.LOG.fatal("Error tearing down shared-site topology: " +
                           str(e))

    def clean_peer_data(self, tunnel, vtep_router, l2dev, az, peer_router):
        """
        :type tunnel: NetData
        :type vtep_router: RouterData
        :type l2dev: L2GWDevice
        :type az: NetData
        :type peer_router: RouterData

        """
        curl_url = get_neutron_api_url(self.api)
        try:
            if l2dev and l2dev.l2conn:
                self.LOG.debug("Cleaning L2GW Conn:" +
                               curl_url +
                               "/l2-gateway-connections/" +
                               str(l2dev.l2conn))
                curl_delete(curl_url + "/l2-gateway-connections/" +
                            str(l2dev.l2conn))

            if l2dev and l2dev.l2gw:
                self.LOG.debug("Cleaning L2GW:" +
                               curl_url + "/l2-gateways/" + str(l2dev.l2gw))
                curl_delete(curl_url + "/l2-gateways/" + str(l2dev.l2gw))

            if vtep_router and vtep_router.router:
                self.api.update_router(vtep_router.router['id'],
                                       {'router': {'routes': None}})
                if vtep_router.if_list:
                    for i in vtep_router.if_list:
                        self.LOG.debug("Removing VTEP interface:" +
                                       str(i) + ' on: ' +
                                       vtep_router.router['id'])
                        self.api.remove_interface_router(
                            vtep_router.router['id'], i)
            if l2dev and l2dev.gwdev:
                self.LOG.debug("Cleaning GW dev:" +
                               curl_url + "/gw/gateway_devices/" +
                               str(l2dev.gwdev))
                curl_delete(curl_url + "/gw/gateway_devices/" +
                            str(l2dev.gwdev))
            if vtep_router and vtep_router.router:
                self.LOG.debug("Deleting VTEP router:" +
                               vtep_router.router['id'])
                self.api.delete_router(vtep_router.router['id'])

            if peer_router and peer_router.router:
                self.api.update_router(peer_router.router['id'],
                                       {'router': {'routes': None}})
                if peer_router.if_list:
                    for i in peer_router.if_list:
                        self.LOG.debug("Removing interface:" +
                                       str(i) + ' on tenant rotuer: ' +
                                       peer_router.router['id'])
                        self.api.remove_interface_router(
                            peer_router.router['id'], i)

            if az:
                if az.subnet:
                    self.LOG.debug("Deleting AZ subnet:" +
                                   az.subnet['id'])
                    self.api.delete_subnet(az.subnet['id'])
                if az.network:
                    self.LOG.debug("Deleting AZ network:" +
                                   az.network['id'])
                    self.api.delete_network(az.network['id'])

            if tunnel:
                if tunnel.subnet:
                    self.LOG.debug("Deleting tunnel subnet:" +
                                   tunnel.subnet['id'])
                    self.api.delete_subnet(tunnel.subnet['id'])
                if tunnel.network:
                    self.LOG.debug("Deleting tunnel network:" +
                                   tunnel.network['id'])
                    self.api.delete_network(tunnel.network['id'])
        except Exception as e:
            self.LOG.fatal("Error tearing down L2GW peer topology: " + str(e))

    def clean_peer(self, topo):
        """
        :type topo: L2GWSiteTopo
        """
        if topo:
            self.clean_peer_data(topo.tunnel,
                                 topo.vtep_router,
                                 topo.l2dev,
                                 topo.az,
                                 topo.peer_router)
