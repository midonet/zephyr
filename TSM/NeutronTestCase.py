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
from collections import namedtuple
from common.Utils import curl_delete
from common.Utils import curl_post
from common.Utils import curl_put
import json
from TSM.TestCase import TestCase
from VTM.NeutronAPI import get_neutron_api_url
from VTM.NeutronAPI import NetData
from VTM.NeutronAPI import RouterData
from PTM.fixtures.MidonetHostSetupFixture import MidonetHostSetupFixture
from PTM.fixtures.NeutronDatabaseFixture import NeutronDatabaseFixture
from PTM.host.Host import Host
from VTM.MNAPI import create_midonet_client
from VTM.Guest import Guest
from common.IP import IP

import neutronclient.v2_0.client as neutron_client

GuestData = namedtuple('GuestData', 'port vm ip')
EdgeData = namedtuple('EdgeData', "edge_net router")


class NeutronTestCase(TestCase):

    #TODO(Joe): Split the cleanup into a per-test-group set of files
    servers = list()
    rmacs = set()
    l2gws = set()
    l2gw_conns = set()
    gws = set()
    fws = set()
    fwps = set()
    fwprs = set()
    fw_ras = set()
    fips = set()
    nports = set()
    nnets = set()
    nsubs = set()
    nrouters = set()
    nr_ifaces = list()

    def clean_topo(self):
        self.clean_firewall_policy_rules()
        self.clean_firewall_rules()
        self.clean_firewalls()
        self.clean_firewall_policies()
        self.clean_remote_mac_entrys()
        self.clean_l2_gateway_conns()
        self.clean_l2_gateway()
        self.clean_fips()
        self.clean_router_routes()
        self.clean_router_ifaces()
        self.clean_gateways()
        self.clean_ports()
        self.clean_routers()
        self.clean_subs()
        self.clean_nets()

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
        self.rmacs.add((gwdev_id, rmac['remote_mac_entry']['id']))
        return rmac['remote_mac_entry']

    def delete_l2_gw_conn(self, l2gwconn_id, clean=True):
        curl_url = get_neutron_api_url(self.api)
        curl_delete(curl_url + "/l2-gateway-connections/" + l2gwconn_id)
        if clean:
            self.l2gw_conns.discard(l2gwconn_id)

    def delete_remote_mac_entry(self, gwdev_id, rme_id, clean=True):
        curl_url = get_neutron_api_url(self.api)
        curl_delete(curl_url +
                    "/gw/gateway_devices/" + str(gwdev_id) +
                    "/remote_mac_entries/" + str(rme_id))
        if clean:
            self.rmacs.discard((gwdev_id, rme_id))

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
        self.gws.add(gw['gateway_device']['id'])
        return gw['gateway_device']

    def update_gw_device(self, gwdev_id, tunnel_ip=None, name=None):
        gwdict = {}
        if name:
            gwdict['name'] = 'vtep_router_' + name
        if tunnel_ip:
            gwdict['tunnel_ips'] = [tunnel_ip]
        curl_req = {"gateway_device": gwdict}

        curl_url = get_neutron_api_url(self.api)
        device_json_ret = curl_put(curl_url + '/gw/gateway_devices/' + gwdev_id, curl_req)
        self.LOG.debug("Update gateway device" + device_json_ret)

    def delete_gateway_device(self, gwdev_id, clean=True):
        curl_url = get_neutron_api_url(self.api) + '/gw/gateway_devices/'
        curl_delete(curl_url + gwdev_id)
        if clean:
            self.gws.discard(gwdev_id)

    def create_uplink_port(self, name, tun_net_id, tun_host, uplink_iface,
                           tun_sub_id, tunnel_ip):
        return self.create_port(name, tun_net_id, host=tun_host,
                                host_iface=uplink_iface, sub_id=tun_sub_id,
                                ip=tunnel_ip)

    def create_l2_gateway(self, name, gwdev_id):
        curl_url = get_neutron_api_url(self.api) + '/l2-gateways'
        l2gw_data = {"l2_gateway": {"name": 'vtep_router_gw_' + name,
                                    "devices": [{"device_id": gwdev_id}],
                                    "tenant_id": "admin"}}

        l2_json_ret = curl_post(curl_url, l2gw_data)
        self.LOG.debug('L2GW ' + name + ': ' + str(l2_json_ret))
        l2gw = json.loads(l2_json_ret)
        self.l2gws.add(l2gw['l2_gateway']['id'])
        return l2gw['l2_gateway']

    def delete_l2_gateway(self, l2gw_id, clean=True):
        curl_url = get_neutron_api_url(self.api)
        curl_delete(curl_url + "/l2-gateway-connections/" + str(l2gw_id))
        if clean:
            self.l2gws.discard(l2gw_id)

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
        self.l2gw_conns.add(l2_conn['l2_gateway_connection']['id'])
        return l2_conn['l2_gateway_connection']

    #TODO(Joe): Move to firewall specific helper file
    def create_firewall(self, fw_policy_id, tenant_id="admin", router_ids=[]):
        fw_data = {'firewall_policy_id': fw_policy_id,
                   'tenant_id': tenant_id,
                   'router_ids': router_ids}
        fw = self.api.create_firewall({'firewall': fw_data})['firewall']
        self.fws.add(fw['id'])
        return fw

    #TODO(Joe): Move to firewall specific helper file
    def delete_firewall(self, fw_id):
        self.fws.discard(fw_id)
        self.api.delete_firewall(fw_id)

    #TODO(Joe): Move to firewall specific helper file
    def create_firewall_policy(self, name, tenant_id='admin'):
        fwp_data = {'name': name,
                    'tenant_id': tenant_id}
        fwp = self.api.create_firewall_policy({'firewall_policy': fwp_data})
        self.fwps.add(fwp['firewall_policy']['id'])
        return fwp['firewall_policy']

    #TODO(Joe): Move to firewall specific helper file
    def delete_firewall_policy(self, fw_id):
        self.fwps.discard(fw_id)
        self.api.delete_firewall_policy(fw_id)

    #TODO(Joe): Move to firewall specific helper file
    def create_firewall_rule(self, source_ip=None, dest_ip=None,
                             action='allow', protocol='tcp',
                             tenant_id='admin'):

        fwpr_data = {'action': action,
                     'protocol': protocol,
                     'ip_version': 4,
                     'shared': False,
                     'source_ip_address': source_ip,
                     'destination_ip_address': dest_ip,
                     'tenant_id': tenant_id}
        fwpr = self.api.create_firewall_rule({'firewall_rule': fwpr_data})
        self.fwprs.add(fwpr['firewall_rule']['id'])
        return fwpr['firewall_rule']

    #TODO(Joe): Move to firewall specific helper file
    def delete_firewall_rule(self, fwpr_id):
        self.fwprs.discard(fwpr_id)
        self.api.delete_firewall_rule(fwpr_id)

    #TODO(Joe): Move to firewall specific helper file
    def insert_firewall_rule(self, fw_policy_id, fw_rule_id):
        data = {"firewall_rule_id": fw_rule_id}
        self.fw_ras.add((fw_policy_id, fw_rule_id))
        self.api.firewall_policy_insert_rule(fw_policy_id, data)

    #TODO(Joe): Move to firewall specific helper file
    def remove_firewall_rule(self, fw_policy_id, fw_rule_id):
        data = {"firewall_rule_id": fw_rule_id}
        self.fw_ras.discard((fw_policy_id, fw_rule_id))
        self.api.firewall_policy_remove_rule(fw_policy_id, data)

    def verify_connectivity(self, vm, dest_ip):
        self.assertTrue(vm.ping(target_ip=dest_ip))

        echo_response = vm.send_echo_request(dest_ip=dest_ip)
        self.assertEqual('ping:echo-reply', echo_response)

        echo_response = vm.send_echo_request(dest_ip=dest_ip)
        self.assertEqual('ping:echo-reply', echo_response)

    def create_vm_server(self, name, net_id, gw_ip):
        port_data = {'name': name,
                     'network_id': net_id,
                     'admin_state_up': True,
                     'tenant_id': 'admin'}
        port = self.api.create_port({'port': port_data})['port']
        ip = port['fixed_ips'][0]['ip_address']
        vm = self.vtm.create_vm(ip=ip, mac=port['mac_address'], gw_ip=gw_ip)
        vm.plugin_vm('eth0', port['id'])
        self.servers.append((vm, ip, port))
        return (port, vm, ip)

    def clean_firewall_policy_rules(self):
        while self.fw_ras:
            (fw_policy_id, fw_rule_id) = self.fw_ras.pop()
            self.remove_firewall_rule(fw_policy_id, fw_rule_id)

    def clean_firewall_rules(self):
        while self.fwprs:
            fwr_id = self.fwprs.pop()
            self.api.delete_firewall_rule(fwr_id)

    def clean_firewall_policies(self):
        while self.fwps:
            fw_policy_id = self.fwps.pop()
            self.api.delete_firewall_policy(fw_policy_id)

    def clean_firewalls(self):
        while self.fws:
            fw_id = self.fws.pop()
            self.api.delete_firewall(fw_id)

    def clean_vm_servers(self):
        while self.servers:
            (vm, ip, port) = self.servers.pop()
            vm.stop_echo_server(ip=ip)
            self.cleanup_vms([(vm, port)])

    def clean_remote_mac_entrys(self):
        while self.rmacs:
            (gwid, rmid) = self.rmacs.pop()
            self.delete_remote_mac_entry(gwid, rmid, clean=False)

    def clean_l2_gateway_conns(self):
        while self.l2gw_conns:
            l2gw_conn_id = self.l2gw_conns.pop()
            self.delete_l2_gw_conn(l2gw_conn_id, clean=False)

    def clean_l2_gateway(self):
        while self.l2gws:
            l2gw_id = self.l2gws.pop()
            self.delete_l2_gateway(l2gw_id, clean=False)

    def clean_gateways(self):
        while self.gws:
            gw_id = self.gws.pop()
            self.delete_gateway_device(gw_id, clean=False)

    def clean_fips(self):
        while self.fips:
            fip_id = self.fips.pop()
            self.api.delete_floatingip(fip_id)

    def clean_router_routes(self):
        for rid in self.nrouters:
            self.api.update_router(rid, {'router': {'routes': None}})

    def clean_router_ifaces(self):
        while self.nr_ifaces:
            (rid, iface) = self.nr_ifaces.pop()
            self.nports.discard(iface['port_id'])
            self.api.remove_interface_router(rid, iface)

    def clean_ports(self):
        while self.nports:
            port_id = self.nports.pop()
            self.api.delete_port(port_id)

    def clean_routers(self):
        while self.nrouters:
            rid = self.nrouters.pop()
            self.api.delete_router(rid)

    def clean_nets(self):
        while self.nnets:
            nid = self.nnets.pop()
            self.api.delete_network(nid)

    def clean_subs(self):
        while self.nsubs:
            sid = self.nsubs.pop()
            self.api.delete_subnet(sid)

    def create_floating_ip(self, port_id, pub_net_id, tenant_id='admin'):
        fip_data = {'port_id': port_id,
                    'tenant_id': tenant_id,
                    'floating_network_id': pub_net_id}
        fip = self.api.create_floatingip({'floatingip': fip_data})
        self.fips.add(fip['floatingip']['id'])
        return fip['floatingip']

    def delete_floating_ip(self, fip_id):
        self.fips.discard(fip_id)
        self.api.delete_floatingip(fip_id)

    def create_port(self, name, net_id, tenant_id='admin', host=None,
                    host_iface=None, sub_id=None, ip=None, mac=None,
                    port_security_enabled=True, device_owner=None,
                    device_id=None):
        port_data = {'name': name,
                     'network_id': net_id,
                     'port_security_enabled': port_security_enabled,
                     'tenant_id': tenant_id}
        if host:
            port_data['binding:host_id'] = host
        if host_iface:
            port_data['binding:profile'] = {'interface_name': host_iface}
        if ip and sub_id:
            port_data['fixed_ips'] = [{'subnet_id': sub_id, 'ip_address': ip}]
        elif ip:
            port_data['fixed_ips'] = [{'ip_address': ip}]
        if device_owner:
            port_data['device_owner'] = device_owner
        if device_id:
            port_data['device_id'] = device_id
        if mac:
            port_data['mac_address'] = mac

        port = self.api.create_port({'port': port_data})
        self.nports.add(port['port']['id'])
        return port['port']

    def delete_port(self, port_id):
        self.nports.discard(port_id)
        self.api.delete_port(port_id)

    def create_network(self, name, admin_state_up=True, tenant_id='admin',
                       external=False, uplink=False):
        net_data = {'name': 'net_' + name,
                    'admin_state_up': admin_state_up,
                    'tenant_id': tenant_id}
        if external:
            net_data['router:external'] = True
        if uplink:
            net_data['provider:network_type'] = 'uplink'

        net = self.api.create_network({'network': net_data})
        self.nnets.add(net['network']['id'])
        return net['network']

    def create_subnet(self, name, net_id, cidr, tenant_id='admin',
                      enable_dhcp=True):
        sub_data = {'name': 'sub_' + name,
                    'network_id': net_id,
                    'ip_version': 4,
                    'enable_dhcp': enable_dhcp,
                    'cidr': cidr,
                    'tenant_id': tenant_id}
        sub = self.api.create_subnet({'subnet': sub_data})
        self.nsubs.add(sub['subnet']['id'])
        return sub['subnet']

    def create_router_interface(self, router_id, port_id=None, sub_id=None):
        data = {}
        if port_id:
            data = {'port_id': port_id}
        elif sub_id:
            data = {'subnet_id': sub_id}
        iface = self.api.add_interface_router(router_id, data)
        self.nr_ifaces.append((router_id, iface))
        return iface

    def remove_router_interface(self, router_id, iface):
        self.nr_ifaces.remove((router_id, iface))
        self.nports.discard(iface['port_id'])
        self.api.remove_interface_router(router_id, iface)

    def create_router(self, name, tenant_id='admin', pub_net_id=None,
                      admin_state_up=True, priv_sub_ids=[]):
        router_data = {'name': name,
                       'admin_state_up': admin_state_up,
                       'tenant_id': tenant_id}
        if pub_net_id:
            router_data['external_gateway_info'] = {'network_id': pub_net_id}
        router = self.api.create_router({'router': router_data})['router']
        for sub_id in priv_sub_ids:
            self.create_router_interface(router['id'], sub_id=sub_id)
        self.nrouters.add(router['id'])
        return router

    def __init__(self, methodName='runTest'):
        super(NeutronTestCase, self).__init__(methodName)
        self.neutron_fixture = None
        """:type: NeutronDatabaseFixture"""
        self.midonet_fixture = None
        """:type: MidonetHostSetupFixture"""
        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet = None
        self.api = None
        """ :type: neutron_client.Client """
        self.mn_api = None

    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(NeutronTestCase, cls)._prepare_class(ptm, vtm, test_case_logger)

        cls.api = cls.vtm.get_client()
        """ :type: neutron_client.Client """
        cls.mn_api = create_midonet_client()

        ext_list = cls.api.list_extensions()['extensions']
        cls.api_extension_map = {v['alias']: v for v in ext_list}

        # Only add the midonet- and neutron-setup fixture once for each scenario.
        if 'midonet-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding midonet-setup fixture')
            midonet_fixture = MidonetHostSetupFixture(cls.vtm, cls.ptm, test_case_logger)
            ptm.add_fixture('midonet-setup', midonet_fixture)

        if 'neutron-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding neutron-setup fixture')
            neutron_fixture = NeutronDatabaseFixture(cls.vtm, cls.ptm, test_case_logger)
            ptm.add_fixture('neutron-setup', neutron_fixture)

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data prior to running
        the test case function.
        """
        self.neutron_fixture = self.ptm.get_fixture('neutron-setup')
        self.LOG.debug("Initializing Test Case Neutron Data from neutron-setup fixture")
        self.main_network = self.neutron_fixture.main_network
        self.main_subnet = self.neutron_fixture.main_subnet
        self.pub_network = self.neutron_fixture.pub_network
        self.pub_subnet = self.neutron_fixture.pub_subnet
        self.api = self.neutron_fixture.api
        self.mn_api = self.neutron_fixture.mn_api
        super(NeutronTestCase, self).run(result)

    #TODO(micucci): Change this to use the GuestData namedtuple
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

    def create_edge_router(self, pub_subnet=None, router_host_name='router1',
                           edge_host_name='edge1', edge_iface_name='eth1', edge_subnet_cidr='172.16.2.0/24'):

        if not pub_subnet:
            pub_subnet = self.pub_subnet

        # Create an uplink network (Midonet-specific extension used for provider:network_type)
        edge_network = self.create_network(edge_host_name, uplink=True)
        self.LOG.debug('Created edge network: ' + str(edge_network))

        # Create uplink network's subnet
        edge_ip = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.2'
        edge_gw = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.1'

        edge_subnet = self.create_subnet(edge_host_name, edge_network['id'],
                                         edge_subnet_cidr, enable_dhcp=False)
        self.LOG.debug('Created edge subnet: ' + str(edge_subnet))

        # Create edge router
        edge_router = self.create_router('edge_router')
        self.LOG.debug('Created edge router: ' + str(edge_router))

        # Create "port" on router by creating a port on the special uplink network
        # bound to the physical interface on the physical host, and then linking
        # that network port to the router's interface.
        edge_port1 = self.create_port(edge_host_name, edge_network['id'],
                                      host=edge_host_name,
                                      host_iface=edge_iface_name,
                                      sub_id=edge_subnet['id'],
                                      ip=edge_ip)
        self.LOG.info('Created physical-bound, edge port: ' + str(edge_port1))
        # Bind port to edge router
        if1 = self.create_router_interface(edge_router['id'], port_id=edge_port1['id'])

        self.LOG.info('Added interface to edge router: ' + str(if1))

        # Bind public network to edge router
        if2 = self.create_router_interface(edge_router['id'], sub_id=pub_subnet['id'])

        self.LOG.info('Added interface to edge router: ' + str(if2))

        # Add the default route
        edge_router = self.api.update_router(edge_router['id'],
                                             {'router': {'routes': [{'destination': '0.0.0.0/0',
                                                                     'nexthop': edge_gw}]}})['router']
        self.LOG.info('Added default route to edge router: ' + str(edge_router))

        router_host = self.ptm.impl_.hosts_by_name[router_host_name]
        """ :type: Host"""
        router_host.add_route(IP.make_ip(pub_subnet['cidr']), IP(edge_ip, '24'))
        self.LOG.info('Added return route to host router')

        return EdgeData(NetData(edge_network, edge_subnet), RouterData(edge_router, [if1, if2]))

    def delete_edge_router(self, edge_data):
        """
        :type edge_data: EdgeData
        :return:
        """
        # Create a public network
        if edge_data:
            if edge_data.router:
                self.LOG.debug("Removing routes from router: " +
                               str(edge_data.router.router))
                self.api.update_router(edge_data.router.router['id'], {'router': {'routes': None}})
                if edge_data.router.if_list:
                    for iface in edge_data.router.if_list:
                        self.LOG.debug("Removing interface: " +
                                       str(iface) + " from router: " +
                                       str(edge_data.router.router))
                        self.api.remove_interface_router(edge_data.router.router['id'], iface)
                self.LOG.debug("Deleting router: " +
                               str(edge_data.router.router))
                self.api.delete_router(edge_data.router.router['id'])
            if edge_data.edge_net.subnet:
                self.LOG.debug("Deleting subnet: " +
                               str(edge_data.edge_net.subnet))
                self.api.delete_subnet(edge_data.edge_net.subnet['id'])
            if edge_data.edge_net.network:
                self.LOG.debug("Deleting network: " +
                               str(edge_data.edge_net.network))
                self.api.delete_network(edge_data.edge_net.network['id'])


class require_extension(object):
    def __init__(self, ext):
        self.ext = ext

    def __call__(self, f):
        def new_tester(slf, *args):
            """
            :param slf: TestCase
            """
            if self.ext in slf.api_extension_map:
                f(slf, *args)
            else:
                slf.skipTest('Skipping because extension: ' + str(self.ext) + ' is not installed')
        return new_tester
