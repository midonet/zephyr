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

from L2GWFixture import L2GWFixture

from common.Utils import curl_post, curl_delete, curl_put
from common.Exceptions import *
from TSM.NeutronTestCase import NeutronTestCase
from VTM.NeutronAPI import *

from collections import namedtuple
import json

L2GWDevice = namedtuple("L2GWDevice", "gwdev l2gw l2conn")
L2GWSiteData = namedtuple("L2GWSiteData",
                          "tunnel_cidr tunnel_ip tunnel_gw tunnel_uplink_host "
                          "tunnel_uplink_iface az_cidr az_gw")
L2GWSiteTopo = namedtuple("L2GWSiteTopo",
                          "tunnel_port tunnel tunnel_ip vtep_router l2dev az peer_router "
                          "peer_router_port")
L2GWPeer = namedtuple("L2GWPeer", "rmac_entry gwdev_id fake_peer_port")
L2GWPeeredTopo = namedtuple("L2GWPeeredTopo", "east west")


class L2GWNeutronTestCase(NeutronTestCase):
    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(L2GWNeutronTestCase, cls)._prepare_class(ptm, vtm,
                                                       test_case_logger)

        # Add the l2gw fixture if it's not already added
        if 'l2gw-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding l2gw-setup fixture')
            ptm.add_fixture('l2gw-setup', L2GWFixture())

    def delete_remote_mac_entry(self, gwdev_id, rme_id):
        curl_url = get_neutron_api_url(self.api)
        curl_delete(curl_url +
                    "/gw/gateway_devices/" + str(gwdev_id) +
                    "/remote_mac_entries/" + str(rme_id))

    def create_gateway_device(self, tunnel_ip, name, vtep_router_id):
        curl_url = get_neutron_api_url(self.api) + '/gw/gateway_devices'
        gw_dev_dict = {"gateway_device": {"name": 'vtep_router_' + name,
                                          "type": 'router_vtep',
                                          "resource_id": vtep_router_id,
                                          "tunnel_ips": [tunnel_ip],
                                          "tenant_id": 'admin'}}
        post_ret = curl_post(curl_url, gw_dev_dict)
        gw = json.loads(post_ret)
        self.LOG.debug('create gateway device: ' + str(gw))
        return gw['gateway_device']

    def update_gw_device(self, gwdev_id, tunnel_ip=None, name=None):
        # Convert it to a VxLAN endpoint (VTEP)
        gwdict = {}
        if name:
            gwdict['name'] = 'vtep_router_' + name
        if tunnel_ip:
            gwdict['tunnel_ips'] = [tunnel_ip]
        curl_req = {"gateway_device": gwdict}

        curl_url = get_neutron_api_url(self.api)
        # Set up GW device
        device_json_ret = curl_put(curl_url + '/gw/gateway_devices/' + gwdev_id, curl_req)
        self.LOG.debug("Update gateway device" + device_json_ret)

    def create_uplink_port(self, name, tun_net_id, tun_host, uplink_iface, tun_sub_id, tunnel_ip):
        tun_port = self.api.create_port(
            {'port': {'name': 'tun_port_' + name,
                      'network_id': tun_net_id,
                      'binding:host_id': tun_host,
                      'binding:profile':
                          {'interface_name': uplink_iface},
                      'fixed_ips': [{'subnet_id': tun_sub_id,
                                     'ip_address': tunnel_ip}],
                      'tenant_id': 'admin'}})
        self.LOG.info('Created ' + name +
                      ' tunnel port: ' + str(tun_port))
        return tun_port['port']

    def create_vtep_network(self, name):
        tun_network = self.api.create_network(
            {'network': {'name': 'tun_' + name,
                         'provider:network_type': 'uplink',
                         'tenant_id': 'admin'}})
        return tun_network['network']

    def create_vtep_subnet(self, name, net_id, cidr):
        tun_subnet = self.api.create_subnet(
            {'subnet': {'name': 'tun_sub_' + name,
                        'network_id': net_id,
                        'enable_dhcp': False,
                        'ip_version': 4,
                        'cidr': cidr,
                        'tenant_id': 'admin'}})
        self.LOG.debug('Created ' + name +
                       ' tunnel subnet: ' + str(tun_subnet))
        return tun_subnet['subnet']

    def create_vtep_router(self, name):
        vtep_router = self.api.create_router(
            {'router': {'name': 'vtep_router_' + name,
                        'tenant_id': 'admin'}})
        self.LOG.debug('Created ' + name +
                       ' VTEP router: ' + str(vtep_router))
        return vtep_router['router']

    def create_l2_gateway(self, name, gwdev_id):
        curl_url = get_neutron_api_url(self.api) + '/l2-gateways'
        l2gw_data = {"l2_gateway": {"name": 'vtep_router_gw_' + name,
                                    "devices": [{"device_id": gwdev_id}],
                                    "tenant_id": "admin"}}

        l2_json_ret = curl_post(curl_url, l2gw_data)
        self.LOG.debug('L2GW ' + name + ': ' + str(l2_json_ret))
        l2gw = json.loads(l2_json_ret)
        return l2gw['l2_gateway']

    def create_l2_gateway_connection(self, az_net_id, segment_id, l2gw_id):
        curl_url = get_neutron_api_url(self.api) + '/l2-gateway-connections'
        l2gw_conn_curl = {"l2_gateway_connection": {
                             "network_id": az_net_id,
                             "segmentation_id": segment_id,
                             "l2_gateway_id": l2gw_id,
                             "tenant_id": "admin"}}

        l2_conn_json_ret = curl_post(curl_url, l2gw_conn_curl)

        self.LOG.debug('L2 Conn: ' + str(l2_conn_json_ret))

        l2_conn = json.loads(l2_conn_json_ret)
        return l2_conn['l2_gateway_connection']

    def create_ghost_port(self, az_net_id, ip, mac, other_port_id):
        ghost_port = self.api.create_port(
                {'port': {
                    'tenant_id': 'admin',
                    'fixed_ips': [{'ip_address': ip}],
                    'name': 'ghost_port_for_west_router',
                    'mac_address': mac,
                    'network_id': az_net_id,
                    'port_security_enabled': False,
                    'device_owner': 'network:remote_site',
                    'device_id': other_port_id}})
        self.LOG.debug("Created ghost port on east network mimicking "
                       "west-side router port: " + str(ghost_port))
        return ghost_port['port']

    def create_remote_mac_entry(self, ip, mac, segment_id, gwdev_id):
        curl_url = get_neutron_api_url(self.api)
        mac_add_data_far = \
            {"remote_mac_entry": {
                "tenant_id": "admin",
                "vtep_address": ip,
                "mac_address": mac,
                "segmentation_id": segment_id}}
        rmac_json_far_ret = \
            curl_post(curl_url + '/gw/gateway_devices/' +
                      str(gwdev_id) + "/remote_mac_entries",
                      json_data=mac_add_data_far)
        self.LOG.debug("RMAC : " + str(rmac_json_far_ret))
        rmac = json.loads(rmac_json_far_ret)
        return rmac['remote_mac_entry']

    def delete_l2_gw_conn(self, l2gwconn_id):
        curl_url = get_neutron_api_url(self.api)
        curl_delete(curl_url + "/l2-gateway-connections/" + l2gwconn_id)

    def setup_peer_l2gw(self, tun_cidr, tun_ip, tun_gw, tun_host, tun_iface,
                        az_cidr, az_gw, segment_id, peer_router, peer_name):

        """
        Setup a single site, ready for peering
        :type l2gw_site_data: L2GWSiteData
        :type segment_id: str
        :type peer_router: dict[str, str]
        :type peer_name: str
        """

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
            tun_network = self.create_vtep_network(peer_name)
            tun_subnet = self.create_vtep_subnet(peer_name, tun_network['id'], tun_cidr)

            # Create VTEP router
            vtep_router = self.create_vtep_router(peer_name)

            # Create "port" on router by creating a port on the
            # special uplink network bound to the physical interface on
            # the physical host, and then linking that network port to
            # the router's interface.
            tun_port = self.create_uplink_port(peer_name, tun_network['id'], tun_host,
                                               tun_iface, tun_subnet['id'], tun_ip)

            # Bind port to edge router
            vtep_tun_if = self.api.add_interface_router(
                    vtep_router['id'],
                    {'port_id': tun_port['id']})
            self.LOG.info('Added interface to ' + peer_name +
                          ' VTEP router: ' + str(vtep_tun_if))

            # Set up GW device
            gw = self.create_gateway_device(tun_ip, peer_name, vtep_router['id'])
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
            l2gw_conn = self.create_l2_gateway_connection(az_net['id'], segment_id, l2gw_id)
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
                    peer_router['id'],
                    {'port_id': peer_router_port['id']})

            # Add the default route through the tunnel uplink
            vtep_router = self.api.update_router(
                    vtep_router['id'],
                    {'router': {
                        'routes': [{'nexthop': tun_gw,
                                    'destination': '0.0.0.0/0'}]}})['router']

            self.LOG.debug(peer_name + ' peer finished: ' + str(peer_router))

            return L2GWSiteTopo(
                    tunnel_port=tun_port,
                    tunnel=NetData(network=tun_network,
                                   subnet=tun_subnet),
                    tunnel_ip=tun_ip,
                    vtep_router=RouterData(router=vtep_router,
                                           if_list=[vtep_tun_if]),
                    l2dev=L2GWDevice(gwdev=gwdev_id,
                                     l2gw=l2gw_id,
                                     l2conn=l2conn_id),
                    az=NetData(network=az_net,
                               subnet=az_sub),
                    peer_router=RouterData(router=peer_router,
                                           if_list=[peer_router_iface]),
                    peer_router_port=peer_router_port)

        except Exception as e:
            self.LOG.fatal("Error creating shared-site topology: " + str(e))
            self.clean_peer_data(
                    tunnel=NetData(network=tun_network,
                                   subnet=tun_subnet),
                    vtep_router=RouterData(router=vtep_router,
                                           if_list=[vtep_tun_if]),
                    l2dev=L2GWDevice(gwdev=gwdev_id,
                                     l2gw=l2gw_id,
                                     l2conn=l2conn_id),
                    az=NetData(network=az_net,
                               subnet=az_sub),
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
            curl_url = get_neutron_api_url(self.api)
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
            rmac = self.create_remote_mac_entry(near_side.tunnel_ip,
                    near_side.peer_router_port['mac_address'], segment_id,
                    far_side.l2dev.gwdev)
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
        try:
            if peer_site:
                if peer_site.rmac_entry:
                    curl_url = (get_neutron_api_url(self.api) +
                                "/gw/gateway_devices/" +
                                str(peer_site.gwdev_id) +
                                "/remote_mac_entries/" +
                                str(peer_site.rmac_entry))
                    self.LOG.debug("Cleaning RMAC entry: " + curl_url)
                    curl_delete(curl_url)
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
