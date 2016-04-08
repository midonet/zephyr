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

from midonetclient.api import MidonetApi
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.cbt import version_config
from tests.neutron.features.lbaas.lbaas_test_utils import LBaaSTestCase
from tests.neutron.features.lbaas.lbaas_test_utils import DEFAULT_POOL_PORT


class TestUpgradeScript(LBaaSTestCase):
    @require_extension('lbaas')
    def test_upgrade_one_of_each_feature(self):
        sg_port = None
        aa_port = None
        pse_port = None

        try:
            self.create_member_net()
            self.create_lbaas_net()
            self.create_pinger_net()
            self.create_lb_router(gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])

            self.create_vip(subnet_id=self.pub_subnet['id'],
                            protocol_port=DEFAULT_POOL_PORT,
                            name='poola-vip1',
                            pool_id=poola['id'])

            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            hm1 = self.create_health_monitor()
            self.create_health_monitor()

            self.associate_health_monitor(hm1['id'], poola['id'])

            self.create_floating_ip(
                port_id=g_pinger.port['id'],
                pub_net_id=self.pub_network['id'])

            sg1 = self.create_security_group(name='test_sg')

            new_port = {'port': {
                'name': 'sg_port_test',
                'network_id': self.main_network['id'],
                'security_groups': [sg1['id']],
                'tenant_id': 'admin'
            }}

            sg_port = self.api.create_port(new_port)['port']

            self.create_router(
                name='test_router',
                pub_net_id=self.pub_network['id'])

            mn_uri = version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url')
            api = MidonetApi(mn_uri, 'admin', 'cat', 'admin')
            """ :type: midonetclient.api.MidonetApi """
            rtrs = api.get_routers(query=None)
            pr = next(r
                      for r in rtrs
                      if r.get_name() == "MidoNet Provider Router")
            """ :type: midonetclient.router.Router """
            rport = (pr.add_port()
                     .port_address('172.16.2.2')
                     .network_address('172.16.2.0')
                     .network_length(24)
                     .create())

            hosts = api.get_hosts()
            edge_host = next(h
                             for h in hosts
                             if h.get_name() == "edge1")
            """ :type: midonetclient.host.Host """

            api.add_host_interface_port(edge_host, rport.get_id(), 'eth1')

            (pr.add_route()
             .type('normal')
             .weight(100)
             .next_hop_gateway('172.16.2.1')
             .next_hop_port(rport.get_id())
             .dst_network_addr('0.0.0.0')
             .dst_network_length(0)
             .src_network_addr('0.0.0.0')
             .src_network_length(0)
             .create())

            import pdb
            pdb.set_trace()

        finally:
            if sg_port:
                self.api.delete_port(sg_port['id'])
            if aa_port:
                self.api.delete_port(aa_port['id'])
            if pse_port:
                self.api.delete_port(pse_port['id'])
            self.clean_vm_servers()
            self.clear_lbaas_data()
            self.clean_topo()
