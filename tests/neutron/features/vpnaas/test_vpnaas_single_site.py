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

from TSM.NeutronTestCase import NeutronTestCase
from tests.scenarios.Scenario_Basic3ComputeWithEdge import Scenario_Basic3ComputeWithEdge
from VTM.Guest import Guest

from collections import namedtuple

SiteData = namedtuple('SiteData', 'net subnet router iface')
VPNData = namedtuple('VPNData', 'ikepol ipsecpol vpnL ipsecL vpnR ipsecR')
TopoData = namedtuple('TopoData', 'sites vpn')

class TestVPNaaSSingleSite(NeutronTestCase):
    @staticmethod
    def supported_physical_topologies():
        return {Scenario_Basic3ComputeWithEdge}

    def setup_vpnaas_neutron_topo(self):
        try:
            gateway_ipL = '10.1.0.1'
            subnet_cidrL = '10.1.0.0/24'
            gateway_ipR = '10.2.0.1'
            subnet_cidrR = '10.2.0.0/24'

            #Create the left side
            privateL = self.api.create_network({'network': {'name': 'privateL',
                                                            'tenant_id': 'admin'}})['network']
            privateLsub = self.api.create_subnet({'subnet': {'name': 'privateLsub',
                                                             'network_id': privateL['id'],
                                                             'ip_version': 4,
                                                             'cidr': subnet_cidrL,
                                                             'gateway_ip': gateway_ipL,
                                                             'tenant_id': 'admin'}})['subnet']
            routerL = self.api.create_router({'router': {'name': 'routerL',
                                                         'tenant_id': 'admin',
                                                         'external_gateway_info': {
                                                             "network_id": self.pub_network['id']
                                                         }}})['router']

            routerL_if1 = self.api.add_interface_router(routerL['id'], {'subnet_id': privateLsub['id']})

            #Create the right side
            privateR = self.api.create_network({'network': {'name': 'privateL',
                                                            'tenant_id': 'admin'}})['network']
            privateRsub = self.api.create_subnet({'subnet': {'name': 'privateLsub',
                                                             'network_id': privateR['id'],
                                                             'ip_version': 4,
                                                             'cidr': subnet_cidrR,
                                                             'gateway_ip': gateway_ipR,
                                                             'tenant_id': 'admin'}})['subnet']
            routerR = self.api.create_router({'router': {'name': 'routerL',
                                                         'tenant_id': 'admin',
                                                         'external_gateway_info': {
                                                             "network_id": self.pub_network['id']
                                                         }}})['router']

            routerR_if1 = self.api.add_interface_router(routerR['id'], {'subnet_id': privateRsub['id']})


            #Create the VPN connections
            ike_pol = self.api.create_ikepolicy({'ikepolicy': {'name': 'main_ike_policy',
                                                               'tenant_id': 'admin',
                                                               }})['ikepolicy']
            ipsec_pol = self.api.create_ipsecpolicy({'ipsecpolicy': {'name': 'main_ipsec_policy',
                                                                     'tenant_id': 'admin',}})['ipsecpolicy']

            # Left-side of VPN connection
            vpn_svcL = self.api.create_vpnservice(
                {'vpnservice': {'name': 'myvpnL',
                                'tenant_id': 'admin',
                                'description': 'My VPN service (Left)',
                                'router_id': routerL['id']}})['vpnservice']

            ipsec_connL = self.api.create_ipsec_site_connection(
                {'ipsec_site_connection': {'name': 'vpnconnectionL',
                                           'tenant_id': 'admin',
                                           'peer_address': gateway_ipR,
                                           'peer_id': gateway_ipR,
                                           'psk': 'secret',
                                           'ikepolicy_id': ike_pol['id'],
                                           'ipsecpolicy_id': ipsec_pol['id'],
                                           'vpnservice_id': vpn_svcL['id']}})['ipsec_site_connection']

            # Right-side of VPN connection
            vpn_svcR = self.api.create_vpnservice(
                {'vpnservice': {'name': 'myvpnR',
                                'tenant_id': 'admin',
                                'description': 'My VPN service (Right)',
                                'router_id': routerR['id']}})['vpnservice']

            ipsec_connR = self.api.create_ipsec_site_connection(
                {'ipsec_site_connection': {'name': 'vpnconnectionR',
                                           'tenant_id': 'admin',
                                           'peer_address': gateway_ipL,
                                           'peer_id': gateway_ipL,
                                           'psk': 'secret',
                                           'ikepolicy_id': ike_pol['id'],
                                           'ipsecpolicy_id': ipsec_pol['id'],
                                           'vpnservice_id': vpn_svcR['id']}})['ipsec_site_connection']
            lt_site = SiteData(privateL, privateLsub, routerL, routerL_if1)
            rt_site = SiteData(privateR, privateRsub, routerR, routerR_if1)
            vpn_data = VPNData(ike_pol, ipsec_pol, vpn_svcL, ipsec_connL, vpn_svcR, ipsec_connR)
            return TopoData([lt_site, rt_site], vpn_data)

        except Exception as e:
            self.LOG.fatal('Error setting up topology: ' + str(e))
            raise e

    def clear_neutron_topo(self, td):
        """
        :type td: TopoData
        :return:
        """

        if td is None:
            return
        for site in td.sites if td.sites is not None else []:
            if site.router is not None:
                if site.iface is not None:
                    self.api.remove_interface_router(site.router['id'], site.iface)
                self.api.delete_router(site.router['id'])
            if site.subnet is not None:
                self.api.delete_subnet(site.subnet['id'])
            if site.net is not None:
                self.api.delete_network(site.net['id'])

        if td.vpn.vpnL is not None:
            self.api.delete_vpnservice(td.vpn.vpnL['id'])
        if td.vpn.ipsecL is not None:
            self.api.delete_ipsec_site_connection(td.vpn.ipsecL['id'])
        if td.vpn.vpnR is not None:
            self.api.delete_vpnservice(td.vpn.vpnR['id'])
        if td.vpn.ipsecR is not None:
            self.api.delete_ipsec_site_connection(td.vpn.ipsecR['id'])
        if td.vpn.ikepol is not None:
            self.api.delete_ikepolicy(td.vpn.ikepol['id'])
        if td.vpn.ipsecpol is not None:
            self.api.delete_ipsecpolicy(td.vpn.ipsecpol['id'])

    def test_vm_communication_through_vpn_tunnel(self):
        vmL1 = None
        vmR1 = None
        td = None
        try:
            td = self.setup_vpnaas_neutron_topo()

            portL1def = {'port': {'name': 'port1',
                                 'network_id': td.sites[0].net['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            portL1 = self.api.create_port(portL1def)['port']
            ipL1 = portL1['fixed_ips'][0]['ip_address']
            self.LOG.info('Created port 1 on left net: ' + str(portL1))
            self.LOG.info("Got VM L1 IP: " + str(ipL1))

            portR1def = {'port': {'name': 'port1',
                                 'network_id': td.sites[1].net['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            portR1 = self.api.create_port(portR1def)['port']
            ipR1 = portR1['fixed_ips'][0]['ip_address']
            self.LOG.info('Created port 1 on right net: ' + str(portR1))
            self.LOG.info("Got VM R1 IP: " + str(ipR1))

            vmL1 = self.vtm.create_vm(ip=ipL1, mac=portL1['mac_address'])
            vmR1 = self.vtm.create_vm(ip=ipR1, mac=portR1['mac_address'])

            vmL1.plugin_vm('eth0', portL1['id'])
            vmR1.plugin_vm('eth0', portR1['id'])

            self.LOG.info('Pinging from VM L1 to VM R1')
            self.assertTrue(vmL1.ping(on_iface='eth0', target_ip=ipR1))

            self.LOG.info('Pinging from VM R1 to VM L1')
            self.assertTrue(vmR1.ping(on_iface='eth0', target_ip=ipL1))

        finally:
            if vmL1 is not None:
                vmL1.terminate()
            if vmR1 is not None:
                vmR1.terminate()
            self.clear_neutron_topo(td)
