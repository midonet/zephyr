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
import json
import logging
import traceback

from zephyr.common.ip import IP
from zephyr.common.utils import curl_delete
from zephyr.common.utils import curl_post
from zephyr.common.utils import curl_put
from zephyr.tsm.test_case import TestCase
from zephyr.vtm.guest import Guest
from zephyr.vtm import neutron_api

GuestData = namedtuple('GuestData', 'port vm ip')
EdgeData = namedtuple('EdgeData', "edge_net router")

MAIN_NET_CIDR = '192.168.0.0/24'
PUB_NET_CIDR = '200.200.0.0/24'


class NeutronTestCase(TestCase):

    # TODO(Joe): Split the cleanup into a per-test-group set of files
    servers = list()
    bgp_speakers = list()
    bgp_peers = list()
    sgs = list()
    sgrs = list()
    rmacs = list()
    l2gws = list()
    l2gw_conns = list()
    gws = list()
    fws = list()
    fwps = list()
    fwprs = list()
    fw_ras = list()
    fips = list()
    nports = list()
    nnets = list()
    nsubs = list()
    nrouters = list()
    nr_ifaces = list()
    logging_resources = list()
    firewall_logs = list()

    def clean_topo(self):
        topo_info = \
            [(self.sgrs, 'security group rule',
              self.api.delete_security_group_rule),
             (self.logging_resources, 'log resource',
              self.delete_logging_resource),
             (self.firewall_logs, 'fw logging object',
              self.remove_firewall_logs),
             (self.bgp_peers, 'bgp peer', self.delete_bgp_peer_curl),
             (self.bgp_speakers, 'bgp speaker', self.delete_bgp_speaker_curl),
             (self.fw_ras, 'firewall policy rule', self.delete_fpr),
             (self.fwprs, 'firewall rule', self.api.delete_firewall_rule),
             (self.fws, 'firewall', self.api.delete_firewall),
             (self.fwps, 'firewall policy', self.api.delete_firewall_policy),
             (self.rmacs, 'remote mac entry', self.delete_rmac),
             (self.l2gw_conns, 'l2 gateway conn', self.delete_l2_gateway_conn),
             (self.l2gws, 'l2 gateway', self.delete_l2gw),
             (self.fips, 'floating ips', self.api.delete_floatingip),
             (self.nrouters, 'router route', self.clear_route),
             (self.nr_ifaces, 'router interface',
              self.remove_interface_router),
             (self.gws, 'gateway', self.delete_gw_dev),
             (self.nports, 'port', self.api.delete_port),
             (self.sgs, 'security group', self.api.delete_security_group),
             (self.nrouters, 'router', self.api.delete_router),
             (self.nsubs, 'subnet', self.api.delete_subnet),
             (self.nnets, 'network', self.api.delete_network)]

        for (items, res_name, del_func) in topo_info:
            self.clean_resource(items, res_name, del_func)

    def add_bgp_speaker_peer(self, bgp_speaker_id, bgp_peer_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-speakers/' +
                    bgp_speaker_id + '/add_bgp_peer.json')
        curl_put(curl_url, {'bgp_peer_id': bgp_peer_id})

    def remove_bgp_speaker_peer(self, bgp_speaker_id, bgp_peer_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-speakers/' +
                    bgp_speaker_id + '/remove_bgp_peer.json')
        curl_put(curl_url, {'bgp_peer_id': bgp_peer_id})

    def create_bgp_speaker_curl(self, name, local_as, router_id,
                                tenant_id='admin', ip_version=4):
        speaker_data = {'name': name,
                        'logical_router': router_id,
                        'tenant_id': tenant_id,
                        'local_as': local_as,
                        'ip_version': ip_version}
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-speakers.json')
        self.LOG.debug("create bgp speaker JSON: " + str(speaker_data))
        post_ret = curl_post(curl_url, {'bgp_speaker': speaker_data})
        self.LOG.debug('Adding BGP speaker: ' + str(speaker_data) +
                       ', return data: ' + str(post_ret))
        speaker = json.loads(post_ret)
        self.bgp_speakers.append(speaker['bgp_speaker']['id'])
        return speaker['bgp_speaker']

    def delete_bgp_speaker(self, bgp_speaker_id):
        self.bgp_speakers.remove(bgp_speaker_id)
        self.delete_bgp_speaker_curl(bgp_speaker_id)

    def delete_bgp_speaker_curl(self, bgp_speaker_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-speakers.json/')
        curl_delete(curl_url + bgp_speaker_id)

    def create_bgp_peer_curl(self, name, peer_ip, remote_as, auth_type='none',
                             tenant_id='admin'):
        peer_data = {'name': name,
                     'tenant_id': tenant_id,
                     'peer_ip': peer_ip,
                     'auth_type': auth_type,
                     'remote_as': remote_as}
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-peers.json')
        self.LOG.debug("create bgp peer JSON: " + str(peer_data))
        post_ret = curl_post(curl_url, {'bgp_peer': peer_data})
        self.LOG.debug('Adding BGP peer: ' + str(peer_data) +
                       ', return data: ' + str(post_ret))
        peer = json.loads(post_ret)
        self.bgp_peers.append(peer['bgp_peer']['id'])
        return peer['bgp_peer']

    def delete_bgp_peer(self, bgp_peer_id):
        self.bgp_peers.remove(bgp_peer_id)
        self.delete_bgp_peer_curl(bgp_peer_id)

    def delete_bgp_peer_curl(self, bgp_peer_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/bgp-peers.json/')
        curl_delete(curl_url + bgp_peer_id)

    def create_security_group(self, name, tenant_id='admin'):
        sg_data = {'name': name,
                   'tenant_id': tenant_id}
        sg = self.api.create_security_group({'security_group': sg_data})
        self.LOG.debug('Created security group: ' + str(sg))
        self.sgs.append(sg['security_group']['id'])
        return sg['security_group']

    def delete_security_group(self, sg_id):
        self.sgs.remove(sg_id)
        self.api.delete_security_group(sg_id)

    def create_security_group_rule(self, sg_id, remote_group_id=None,
                                   tenant_id='admin', direction='ingress',
                                   protocol=None, port_range_min=None,
                                   port_range_max=None, ethertype='IPv4',
                                   remote_ip_prefix=None):
        sgr_data = {'security_group_id': sg_id,
                    'remote_group_id': remote_group_id,
                    'direction': direction,
                    'protocol': protocol,
                    'port_range_min': port_range_min,
                    'port_range_max': port_range_max,
                    'ethertype': ethertype,
                    'remote_ip_prefix': remote_ip_prefix,
                    'tenant_id': tenant_id}
        sgr = self.api.create_security_group_rule(
            {'security_group_rule': sgr_data})
        self.LOG.debug('Created security group rule: ' + str(sgr))
        self.sgrs.append(sgr['security_group_rule']['id'])
        return sgr['security_group_rule']

    def delete_fpr(self, fw_policy_id, fw_rule_id):
        data = {"firewall_rule_id": fw_rule_id}
        self.api.firewall_policy_remove_rule(fw_policy_id, data)

    def delete_security_group_rule(self, sgr_id):
        self.sgrs.remove(sgr_id)
        self.api.delete_security_group_rule(sgr_id)

    def create_remote_mac_entry(self, ip, mac, segment_id, gwdev_id):
        curl_url = neutron_api.get_neutron_api_url(self.api)
        mac_add_data_far = \
            {"remote_mac_entry": {
                "tenant_id": "admin",
                "vtep_address": ip,
                "mac_address": mac,
                "segmentation_id": segment_id}}
        self.LOG.debug("RMAC JSON: " + str(mac_add_data_far))
        rmac_json_far_ret = \
            curl_post(curl_url + '/gw/gateway_devices/' +
                      str(gwdev_id) + "/remote_mac_entries",
                      json_data=mac_add_data_far)
        self.LOG.debug("Adding RMAC JSON: " + str(mac_add_data_far) +
                       ', return data: ' + str(rmac_json_far_ret))
        rmac = json.loads(rmac_json_far_ret)
        self.rmacs.append((gwdev_id, rmac['remote_mac_entry']['id']))
        self.LOG.debug('Created RMAC entry: ' + str(rmac))
        return rmac['remote_mac_entry']

    def delete_l2_gateway_conn(self, l2gwconn_id):
        curl_url = neutron_api.get_neutron_api_url(self.api)
        curl_delete(curl_url + "/l2-gateway-connections/" + l2gwconn_id)

    def delete_l2_gw_conn(self, l2gwconn_id):
        self.delete_l2_gateway_conn(l2gwconn_id)
        self.l2gw_conns.remove(l2gwconn_id)

    def delete_rmac(self, gwdev_id, rme_id):
        curl_url = neutron_api.get_neutron_api_url(self.api)
        curl_delete(curl_url +
                    "/gw/gateway_devices/" + str(gwdev_id) +
                    "/remote_mac_entries/" + str(rme_id))

    def delete_remote_mac_entry(self, gwdev_id, rme_id):
        self.delete_rmac(gwdev_id, rme_id)
        self.rmacs.remove((gwdev_id, rme_id))

    def create_gateway_device(self, resource_id, dev_type='router_vtep',
                              tunnel_ip=None, name=None):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/gw/gateway_devices')
        gw_dict = {"type": dev_type,
                   "resource_id": resource_id,
                   "tenant_id": 'admin'}

        if dev_type == 'router_vtep':
            gw_dict["name"] = 'gwdev_' + name
            gw_dict["tunnel_ips"] = [tunnel_ip]

        gw_dev_dict = {"gateway_device": gw_dict}

        self.LOG.debug("create gateway device JSON: " + str(gw_dev_dict))
        post_ret = curl_post(curl_url, gw_dev_dict)
        self.LOG.debug('Adding gateway device: ' + str(gw_dev_dict) +
                       ', return data: ' + str(post_ret))
        gw = json.loads(post_ret)
        self.gws.append(gw['gateway_device']['id'])
        self.LOG.debug("Created GW Device: " + str(gw))
        return gw['gateway_device']

    def update_gw_device(self, gwdev_id, tunnel_ip=None, name=None):
        gwdict = {}
        if name:
            gwdict['name'] = 'vtep_router_' + name
        if tunnel_ip:
            gwdict['tunnel_ips'] = [tunnel_ip]
        curl_req = {"gateway_device": gwdict}

        curl_url = neutron_api.get_neutron_api_url(self.api)
        device_json_ret = curl_put(
            curl_url + '/gw/gateway_devices/' + gwdev_id, curl_req)
        self.LOG.debug("Update gateway device" + device_json_ret)

    def delete_gw_dev(self, gwdev_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/gw/gateway_devices/')
        curl_delete(curl_url + gwdev_id)

    def delete_gateway_device(self, gwdev_id):
        self.delete_gw_dev(gwdev_id)
        self.gws.remove(gwdev_id)

    def create_uplink_port(self, name, tun_net_id, tun_host, uplink_iface,
                           tun_sub_id, tunnel_ip):
        return self.create_port(name, tun_net_id, host=tun_host,
                                host_iface=uplink_iface, sub_id=tun_sub_id,
                                ip=tunnel_ip)

    def create_l2_gateway(self, name, gwdev_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/l2-gateways')
        l2gw_data = {"l2_gateway": {"name": 'l2gw_' + name,
                                    "devices": [{"device_id": gwdev_id}],
                                    "tenant_id": "admin"}}

        self.LOG.debug("L2GW JSON: " + str(l2gw_data))
        l2_json_ret = curl_post(curl_url, l2gw_data)
        self.LOG.debug('Adding L2GW ' + name + ': ' + str(l2gw_data) +
                       ', return data: ' + str(l2_json_ret))
        l2gw = json.loads(l2_json_ret)
        self.l2gws.append(l2gw['l2_gateway']['id'])
        self.LOG.debug("Created L2GW: " + str(l2gw))
        return l2gw['l2_gateway']

    def delete_l2gw(self, l2gw_id):
        curl_url = neutron_api.get_neutron_api_url(self.api)
        curl_delete(curl_url + "/l2-gateways/" + str(l2gw_id))

    def delete_l2_gateway(self, l2gw_id):
        self.delete_l2gw(l2gw_id)
        self.l2gws.remove(l2gw_id)

    def create_l2_gateway_connection(self, net_id, segment_id, l2gw_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/l2-gateway-connections')
        l2gw_conn_curl = {"l2_gateway_connection": {
            "network_id": net_id,
            "segmentation_id": segment_id,
            "l2_gateway_id": l2gw_id,
            "tenant_id": "admin"}}

        self.LOG.debug("L2 Conn JSON: " + str(l2gw_conn_curl))
        l2_conn_json_ret = curl_post(curl_url, l2gw_conn_curl)

        self.LOG.debug('Adding L2 Conn: ' + str(l2_conn_json_ret))

        l2_conn = json.loads(l2_conn_json_ret)
        self.l2gw_conns.append(l2_conn['l2_gateway_connection']['id'])
        self.LOG.debug("Created GW Device: " + str(l2_conn))
        return l2_conn['l2_gateway_connection']

    # TODO(Joe): Move to firewall specific helper file
    def create_firewall(self, fw_policy_id, tenant_id="admin",
                        router_ids=list()):
        fw_data = {'firewall_policy_id': fw_policy_id,
                   'tenant_id': tenant_id,
                   'router_ids': router_ids}
        fw = self.api.create_firewall({'firewall': fw_data})['firewall']
        self.fws.append(fw['id'])
        return fw

    # TODO(Joe): Move to firewall specific helper file
    def delete_firewall(self, fw_id):
        self.fws.remove(fw_id)
        self.api.delete_firewall(fw_id)

    # TODO(Joe): Move to firewall specific helper file
    def create_firewall_policy(self, name, tenant_id='admin'):
        fwp_data = {'name': name,
                    'tenant_id': tenant_id}
        fwp = self.api.create_firewall_policy({'firewall_policy': fwp_data})
        self.fwps.append(fwp['firewall_policy']['id'])
        return fwp['firewall_policy']

    # TODO(Joe): Move to firewall specific helper file
    def delete_firewall_policy(self, fw_id):
        self.fwps.remove(fw_id)
        self.api.delete_firewall_policy(fw_id)

    # TODO(Joe): Move to firewall specific helper file
    def create_firewall_rule(self, source_ip=None, dest_ip=None,
                             src_port=None, dest_port=None,
                             action='allow', protocol='tcp',
                             tenant_id='admin'):

        fwpr_data = {'action': action,
                     'protocol': protocol,
                     'ip_version': 4,
                     'shared': False,
                     'source_ip_address': source_ip,
                     'destination_ip_address': dest_ip,
                     'tenant_id': tenant_id}

        if dest_port is not None:
            fwpr_data['destination_port'] = dest_port
        if src_port is not None:
            fwpr_data['source_port'] = src_port
        fwpr = self.api.create_firewall_rule({'firewall_rule': fwpr_data})
        self.fwprs.append(fwpr['firewall_rule']['id'])
        return fwpr['firewall_rule']

    # TODO(Joe): Move to firewall specific helper file
    def delete_firewall_rule(self, fwpr_id):
        self.fwprs.remove(fwpr_id)
        self.api.delete_firewall_rule(fwpr_id)

    # TODO(Joe): Move to firewall specific helper file
    def insert_firewall_rule(self, fw_policy_id, fw_rule_id):
        data = {"firewall_rule_id": fw_rule_id}
        self.fw_ras.append((fw_policy_id, fw_rule_id))
        self.api.firewall_policy_insert_rule(fw_policy_id, data)

    # TODO(Joe): Move to firewall specific helper file
    def remove_firewall_rule(self, fw_policy_id, fw_rule_id):
        self.fw_ras.remove((fw_policy_id, fw_rule_id))
        data = {"firewall_rule_id": fw_rule_id}
        self.api.firewall_policy_remove_rule(fw_policy_id, data)

    def create_logging_resource(
            self, name, description='Logger resource', enabled=True):

        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/logging/logging_resources')
        curl_data = {
            'logging_resource': {
                'name': name,
                'description': description,
                'enabled': enabled,
                'tenant_id': 'admin'
            }
        }

        self.LOG.debug("Log Resource JSON: " + str(curl_data))
        json_ret = curl_post(curl_url, curl_data)

        self.LOG.debug('Adding Log Resource: ' + str(json_ret))

        logr = json.loads(json_ret)
        self.logging_resources.append(logr['logging_resource']['id'])
        self.LOG.debug('Created logging resource: ' + str(logr))
        return logr['logging_resource']

    def delete_logging_resource(self, lgr_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/logging/logging_resources/' + str(lgr_id))
        curl_delete(curl_url)
        self.logging_resources.remove(lgr_id)
        self.LOG.debug('Deleted logging resource: ' + str(lgr_id))

    def create_firewall_log(self, res_id, fw_event, fw_id,
                            description="Firewall log object"):

        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/logging/logging_resources/' + str(res_id) +
                    '/firewall_logs')
        curl_data = {
            'firewall_log': {
                'fw_event': fw_event,
                'description': description,
                'firewall_id': fw_id,
                'tenant_id': 'admin'
            }
        }

        self.LOG.debug("FW log JSON: " + str(curl_data))
        json_ret = curl_post(curl_url, curl_data)

        self.LOG.debug('Adding FW log: ' + str(json_ret))

        fwlog = json.loads(json_ret)
        self.LOG.debug('Created firewall log: ' + str(fwlog))
        self.firewall_logs.append(
            (res_id, fwlog['firewall_log']['id']))
        return fwlog['firewall_log']

    def update_firewall_log(self, fwlog_id, res_id, fw_event, fw_id,
                            description="Firewall log object"):

        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/logging/logging_resources/' + str(res_id) +
                    '/firewall_logs/' + str(fwlog_id))
        curl_data = {
            'firewall_log': {
                'fw_event': fw_event,
                'description': description,
                'firewall_id': fw_id
            }
        }

        self.LOG.debug("FW log JSON: " + str(curl_data))
        json_ret = curl_put(curl_url, curl_data)

        self.LOG.debug('Adding FW log: ' + str(json_ret))

        fwlog = json.loads(json_ret)

        self.LOG.debug('Updated firewall log: ' + str(fwlog))
        return fwlog['firewall_log']

    def delete_firewall_log(self, res_id, fwlog_id):
        curl_url = (neutron_api.get_neutron_api_url(self.api) +
                    '/logging/logging_resources/' + str(res_id) +
                    '/firewall_logs/' + str(fwlog_id))
        curl_delete(curl_url)
        self.firewall_logs.remove((res_id, fwlog_id))
        self.LOG.debug('Deleted firewall log object: ' + str(fwlog_id))

    def remove_firewall_logs(self, id_tuple):
        self.delete_firewall_log(*id_tuple)

    def verify_tcp_connectivity(self, vm, dest_ip, dest_port):
        echo_response = vm.send_echo_request(dest_ip=dest_ip,
                                             dest_port=dest_port)
        self.assertEqual('ping:echo-reply', echo_response)

    def verify_connectivity(self, vm, dest_ip, count=2):
        self.assertTrue(vm.ping(target_ip=dest_ip, count=count, timeout=20))

        for i in range(0, count):
            echo_response = vm.send_echo_request(dest_ip=dest_ip)
            self.assertEqual('ping:echo-reply', echo_response)

        # TODO(micucci): Fix UDP
        # for i in range(0, count):
        #     echo_response = vm.send_echo_request(dest_ip=dest_ip,
        #                                          protocol='udp')
        #     self.assertEqual('ping:echo-reply', echo_response)

    def create_vm_server(self, name, net_id, gw_ip, sgs=list(),
                         allowed_address_pairs=None, hv_host=None):
        """
        :rtype: (str, zephyr.vtm.guest.Guest, str)
        """
        port_data = {'name': name,
                     'network_id': net_id,
                     'admin_state_up': True,
                     'tenant_id': 'admin'}
        if sgs:
            port_data['security_groups'] = sgs
        if allowed_address_pairs:
            port_data['allowed_address_pairs'] = (
                [{'ip_address': pair[0],
                  'mac_address': pair[1]} if len(pair) > 1
                 else {'ip_address': pair[0]}
                 for pair in allowed_address_pairs])
        port = self.api.create_port({'port': port_data})['port']
        ip = port['fixed_ips'][0]['ip_address']
        vm = self.vtm.create_vm(name=name,
                                ip=ip,
                                mac=port['mac_address'],
                                gw_ip=gw_ip,
                                hv_host=hv_host)
        vm.plugin_vm('eth0', port['id'])
        self.servers.append((vm, ip, port))
        return port, vm, ip

    def clean_resource(self, items, res_name, del_func):
        for item in items:
            try:
                self.LOG.debug('Deleting ' + res_name + ' ' + str(item))
                if isinstance(item, basestring):
                    del_func(item)
                else:
                    del_func(*item)
            except Exception:
                traceback.print_exc()
        if res_name != 'router route':
            del items[:]

    def clean_vm_servers(self):
        for (vm, ip, port) in self.servers:
            try:
                self.LOG.debug('Deleting server ' + str((vm, ip, port)))
                vm.stop_echo_server(ip=ip)
                self.cleanup_vms([(vm, port)])
            except Exception:
                traceback.print_exc()
        del self.servers[:]

    def clear_route(self, rid):
        if 'extraroute' in self.api_extension_map:
            self.api.update_router(rid, {'router': {'routes': None}})

    def add_routes(self, rid, route_dest_gw_pairs):
        if 'extraroute' in self.api_extension_map:
            route_list = []
            for route_pair in route_dest_gw_pairs:
                route_dest = route_pair[0]
                route_gw = route_pair[1]
                route_list.append({'destination': route_dest,
                                   'nexthop': route_gw})
            new_router = self.api.update_router(
                rid,
                {'router': {'routes': route_list}})['router']
            self.LOG.info('Added routes to router: ' +
                          str(new_router))
            return new_router
        return None

    def remove_interface_router(self, rid, iface):
        if iface['port_id'] in self.nports:
            self.nports.remove(iface['port_id'])
        self.api.remove_interface_router(rid, iface)

    def create_floating_ip(self, pub_net_id, port_id=None, tenant_id='admin'):
        fip_data = {
            'tenant_id': tenant_id,
            'floating_network_id': pub_net_id}
        if port_id:
            fip_data['port_id'] = port_id
        fip = self.api.create_floatingip({'floatingip': fip_data})
        self.fips.append(fip['floatingip']['id'])
        self.LOG.debug('Created Neutron FIP: ' + str(fip))
        return fip['floatingip']

    def update_floating_ip(self, fip_id,
                           pub_net_id=None, port_id=None):
        fip_data = {}
        if pub_net_id:
            fip_data['floating_network_id'] = pub_net_id
        if port_id:
            fip_data['port_id'] = port_id
        fip = self.api.update_floatingip(fip_id, {'floatingip': fip_data})
        self.LOG.debug('Updated Neutron FIP: ' + str(fip))
        return fip['floatingip']

    def delete_floating_ip(self, fip_id):
        self.fips.remove(fip_id)
        self.api.delete_floatingip(fip_id)

    def create_port(self, name, net_id, tenant_id='admin', host=None,
                    host_iface=None, sub_id=None, ip=None, mac=None,
                    port_security_enabled=True, device_owner=None,
                    device_id=None, sg_ids=None, allowed_address_pairs=None):
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
        if sg_ids:
            port_data['security_groups'] = sg_ids
        if allowed_address_pairs:
            port_data['allowed_address_pairs'] = (
                [{'ip_address': pair[0],
                  'mac_address': pair[1]} if len(pair) > 1
                 else {'ip_address': pair[0]}
                 for pair in allowed_address_pairs])

        port = self.api.create_port({'port': port_data})
        self.nports.append(port['port']['id'])
        self.LOG.debug('Created Neutron port: ' + str(port))
        return port['port']

    def delete_port(self, port_id):
        self.nports.remove(port_id)
        self.api.delete_port(port_id)

    def create_network(self, name, admin_state_up=True, tenant_id='admin',
                       external=False, uplink=False,
                       port_security_enabled=True):
        net_data = {'name': 'net_' + name,
                    'admin_state_up': admin_state_up,
                    'tenant_id': tenant_id}
        if external:
            net_data['router:external'] = True
        if uplink:
            net_data['provider:network_type'] = 'uplink'
        if not port_security_enabled:
            net_data['port_security_enabled'] = False

        net = self.api.create_network({'network': net_data})
        self.nnets.append(net['network']['id'])
        self.LOG.debug('Created Neutron network: ' + str(net))
        return net['network']

    def delete_network(self, net_id):
        self.nnets.remove(net_id)
        self.api.delete_network(net_id)

    def create_subnet(self, name, net_id, cidr, tenant_id='admin',
                      enable_dhcp=True):
        sub_data = {'name': 'sub_' + name,
                    'network_id': net_id,
                    'ip_version': 4,
                    'enable_dhcp': enable_dhcp,
                    'cidr': cidr,
                    'tenant_id': tenant_id}
        sub = self.api.create_subnet({'subnet': sub_data})
        self.nsubs.append(sub['subnet']['id'])
        self.LOG.debug('Created Neutron subnet: ' + str(sub))
        return sub['subnet']

    def delete_subnet(self, sub_id):
        self.nsubs.remove(sub_id)
        self.api.delete_subnet(sub_id)

    def create_router_interface(self, router_id, port_id=None, sub_id=None):
        data = {}
        if port_id:
            data = {'port_id': port_id}
        elif sub_id:
            data = {'subnet_id': sub_id}
        iface = self.api.add_interface_router(router_id, data)
        self.nr_ifaces.append((router_id, iface))
        self.LOG.debug('Added Neutron interface: ' + str(iface) +
                       ' to router: ' + str(router_id))
        return iface

    def remove_router_interface(self, router_id, iface):
        self.nr_ifaces.remove((router_id, iface))
        self.nports.remove(iface['port_id'])
        self.api.remove_interface_router(router_id, iface)

    def create_router(self, name, tenant_id='admin', pub_net_id=None,
                      admin_state_up=True, priv_sub_ids=list()):
        router_data = {'name': name,
                       'admin_state_up': admin_state_up,
                       'tenant_id': tenant_id}
        if pub_net_id:
            router_data['external_gateway_info'] = {'network_id': pub_net_id}
        router = self.api.create_router({'router': router_data})['router']
        for sub_id in priv_sub_ids:
            self.create_router_interface(router['id'], sub_id=sub_id)
        self.nrouters.append(router['id'])
        self.LOG.debug('Created Neutron router: ' + str(router))
        return router

    def delete_router(self, rid):
        self.nrouters.remove(rid)
        self.api.delete_router(rid)

    def __init__(self, method_name='runTest'):
        super(NeutronTestCase, self).__init__(method_name)
        self.neutron_fixture = None
        """:type: NeutronDatabaseFixture"""
        self.midonet_fixture = None
        """:type: MidonetHostSetupFixture"""
        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet = None
        self.init_networks = True

    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(NeutronTestCase, cls)._prepare_class(ptm, vtm, test_case_logger)

        cls.api = cls.vtm.get_client()
        """ :type: neutron_client.Client """

        ext_list = cls.api.list_extensions()['extensions']
        cls.api_extension_map = {v['alias']: v for v in ext_list}

    def init_main_pub_networks(self):
        self.LOG.debug(
            "Initializing Main and Public Networks")
        self.main_network = self.create_network('main')
        self.main_subnet = self.create_subnet(
            'main_sub', net_id=self.main_network['id'], cidr=MAIN_NET_CIDR)
        self.pub_network = self.create_network('public', external=True)
        self.pub_subnet = self.create_subnet(
            'public_sub', net_id=self.pub_network['id'], cidr=PUB_NET_CIDR)
        self.public_router = self.create_router(
            'main_pub_router', pub_net_id=self.pub_network['id'],
            priv_sub_ids=[self.main_subnet['id']])

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data
        prior to running the test case function.
        """
        try:
            if self.init_networks is True:
                self.init_main_pub_networks()
            super(NeutronTestCase, self).run(result)
        finally:
            self.clean_vm_servers()
            self.clean_topo()

    # TODO(micucci): Change this to use the GuestData namedtuple
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

    def create_edge_router(self, pub_subnets=None, router_host_name='router1',
                           edge_host_name='edge1', edge_iface_name='eth1',
                           edge_subnet_cidr='172.16.2.0/24', gateway=True,
                           gateway_networks=None):

        if not pub_subnets:
            pub_subnets = [self.pub_subnet]

        if not gateway_networks:
            gateway_networks = [self.pub_network]

        # Create an uplink network (Midonet-specific extension used for
        # provider:network_type)
        edge_network = self.create_network(edge_host_name, uplink=True)

        # Create uplink network's subnet
        edge_ip = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.2'
        edge_gw = '.'.join(edge_subnet_cidr.split('.')[:-1]) + '.1'

        edge_subnet = self.create_subnet(edge_host_name, edge_network['id'],
                                         edge_subnet_cidr, enable_dhcp=False)

        # Create edge router
        edge_router = self.create_router('edge_router')

        # Create "port" on router by creating a port on the special uplink
        # network bound to the physical interface on the physical host,
        # and then linking that network port to the router's interface.
        edge_port1 = self.create_port(edge_host_name, edge_network['id'],
                                      host=edge_host_name,
                                      host_iface=edge_iface_name,
                                      sub_id=edge_subnet['id'],
                                      ip=edge_ip)
        # Bind port to edge router
        if_list = [self.create_router_interface(
            edge_router['id'], port_id=edge_port1['id'])]

        if gateway:
            for sub in pub_subnets:
                # Bind public network to edge router
                if_list.append(self.create_router_interface(
                    edge_router['id'], sub_id=sub['id']))
        else:
            for net in gateway_networks:
                pub_port = self.create_port(net['name'] + '_gwport',
                                            net['id'])
                if_list.append(self.create_router_interface(
                    edge_router['id'],
                    port_id=pub_port['id']))

        # Add the default route
        edge_router = self.api.update_router(
            edge_router['id'],
            {'router': {'routes': [{'destination': '0.0.0.0/0',
                                    'nexthop': edge_gw}]}})['router']
        self.LOG.info('Added default route to edge router: ' +
                      str(edge_router))

        router_host = self.ptm.hosts_by_name[router_host_name]
        """ :type: Host"""
        for sub in pub_subnets:
            router_host.add_route(
                IP.make_ip(sub['cidr']), IP(edge_ip, '24'))
        self.LOG.info('Added return routes to host router')

        return EdgeData(
            neutron_api.NetData(
                edge_network,
                edge_subnet),
            neutron_api.RouterData(edge_router, if_list))

    def delete_edge_router(self, edge_data):
        """
        :type edge_data: EdgeData
        :return:
        """
        # Create a public network
        if edge_data:
            if edge_data.router:
                er = edge_data.router.router
                self.LOG.debug("Removing routes from router: " + str(er))
                self.clear_route(er['id'])
                if edge_data.router.if_list:
                    for iface in edge_data.router.if_list:
                        self.LOG.debug("Removing interface: " +
                                       str(iface) + " from router: " +
                                       str(er))
                        self.remove_interface_router(er['id'], iface)
                self.LOG.debug("Deleting router: " + str(er))
                self.delete_router(er['id'])
            if edge_data.edge_net.subnet:
                es = edge_data.edge_net.subnet
                self.LOG.debug("Deleting subnet: " + str(es))
                self.delete_subnet(es['id'])
            if edge_data.edge_net.network:
                en = edge_data.edge_net.network
                self.LOG.debug("Deleting network: " + str(en))
                self.delete_network(en['id'])


class require_extension(object):  # noqa
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
                slf.skipTest('Skipping because extension: ' +
                             str(self.ext) + ' is not installed')
        return new_tester
