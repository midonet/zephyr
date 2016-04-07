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
            self.create_member_net(name='main')
            self.create_lbaas_net(name='main')
            self.create_pinger_net(name='main')
            self.create_lb_router(name='main',
                                  gw_net_id=self.pub_network['id'])

            self.create_lbaas_net(name='main2',
                                  cidr='192.168.122.0/24')
            self.create_lb_router(name='main2',
                                  gw_net_id=self.pub_network['id'])

            poola = self.create_pool(
                subnet_id=self.topos['main']['lbaas']['subnet']['id'])
            poolb = self.create_pool(
                subnet_id=self.topos['main2']['lbaas']['subnet']['id'])

            self.create_vip(subnet_id=self.pub_subnet['id'],
                            protocol_port=DEFAULT_POOL_PORT,
                            name='poola-vip1',
                            pool_id=poola['id'])

            self.create_vip(subnet_id=self.pub_subnet['id'],
                            protocol_port=DEFAULT_POOL_PORT+1,
                            name='poolb-vip1',
                            pool_id=poolb['id'])

            vms = self.create_member_vms(num_members=2)
            g1 = vms[0]
            g2 = vms[1]

            g_pinger = self.create_pinger_vm()

            self.create_member(pool_id=poola['id'],
                               ip=g1.ip)
            self.create_member(pool_id=poola['id'],
                               ip=g2.ip)

            self.create_member(pool_id=poolb['id'],
                               ip=g1.ip)

            self.create_health_monitor()

            hm1 = self.create_health_monitor()
            self.associate_health_monitor(hm1['id'], poola['id'])

            hm2 = self.create_health_monitor()
            self.associate_health_monitor(hm2['id'], poolb['id'])

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
            """ :type: midonetclient.port.Port """

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

            pr_bgp = (rport.add_bgp()
                      .peer_addr('172.16.2.1')
                      .peer_as('54321')
                      .local_as('12345')
                      .create())

            (pr_bgp.add_ad_route()
             .nw_prefix('200.200.0.0')
             .nw_prefix_length(24)
             .create())

            new_br = (api.add_bridge()
                      .tenant_id('admin')
                      .name('mn_br_test')
                      .disable_anti_spoof(True)
                      .create())
            """ :type: midonetclient.bridge.Bridge"""
            (new_br.add_dhcp_subnet()
             .default_gateway('10.200.200.1')
             .subnet_prefix('10.200.200.0')
             .subnet_length(24)
             .enabled(True)
             .create())
            """ :type: midonetclient.dhcp_subnet.DhcpSubnet"""

            br_port = (new_br.add_port()
                       .create())
            """ :type: midonetclient.port.Port"""

            new_br.disable_anti_spoof(True)

            new_rtr = (api.add_router()
                       .name('mn_rtr_test')
                       .tenant_id('admin')
                       .create())
            """ :type: midonetclient.router.Router"""

            rtr_port = (new_rtr.add_port()
                        .port_address('10.200.200.1')
                        .network_address('10.200.200.0')
                        .network_length(24)
                        .port_mac("AA:BB:CC:DD:EE:FF")
                        .create())
            """ :type: midonetclient.port.Port"""
            br_port.link(rtr_port.get_id())

            rtr_bgp_port1 = (new_rtr.add_port()
                             .port_address('10.200.200.5')
                             .network_address('10.200.200.0')
                             .network_length(24)
                             .port_mac("BB:CC:DD:EE:FF:00")
                             .create())
            """ :type: midonetclient.port.Port"""

            rtr_bgp_port2 = (new_rtr.add_port()
                             .port_address('10.200.200.6')
                             .network_address('10.200.200.0')
                             .network_length(24)
                             .port_mac("CC:DD:EE:FF:00:11")
                             .create())
            """ :type: midonetclient.port.Port"""

            tr_bgp1 = (rtr_bgp_port1.add_bgp()
                       .peer_addr('172.16.2.1')
                       .peer_as('23456')
                       .local_as('65432')
                       .create())
            (tr_bgp1.add_ad_route()
             .nw_prefix('10.200.200.0')
             .nw_prefix_length(24)
             .create())

            tr_bgp2 = (rtr_bgp_port1.add_bgp()
                       .peer_addr('172.16.3.1')
                       .peer_as('34567')
                       .local_as('76543')
                       .create())
            (tr_bgp2.add_ad_route()
             .nw_prefix('10.200.201.0')
             .nw_prefix_length(24)
             .create())

            tr_bgp3 = (rtr_bgp_port2.add_bgp()
                       .peer_addr('172.16.3.1')
                       .peer_as('34567')
                       .local_as('76543')
                       .create())
            (tr_bgp3.add_ad_route()
             .nw_prefix('10.200.201.0')
             .nw_prefix_length(24)
             .create())

            tr = next(r
                      for r in rtrs
                      if r.get_name() == "test_router")
            """ :type: midonetclient.router.Router"""

            (tr.add_port()
             .port_address('10.155.155.5')
             .network_address('10.155.155.0')
             .network_length(24)
             .port_mac("00:11:22:AA:BB:CC")
             .create())
            lb_net = self.topos['main']['lbaas']['network']
            lb_rtr_id = self.topos['main']['router']['id']
            bridges = api.get_bridges(query=None)
            old_br = next(b
                          for b in bridges
                          if b.get_id() == lb_net['id'])
            """ :type: midonetclient.bridge.Bridge"""

            if old_br:
                (old_br.add_port()
                 .create())
                old_br.disable_anti_spoof(True).update()

            pg = (api.add_port_group()
                  .tenant_id('admin')
                  .name('pg-test')
                  .stateful(True)
                  .create())
            """ :type: midonetclient.port_group.PortGroup"""

            (pg.add_port_group_port()
             .port_id(br_port.get_id())
             .create())

            lb_obj = (api.add_load_balancer()
                      .create())
            lb2_rtr = api.get_router(lb_rtr_id)
            lb2_obj = api.get_load_balancer(lb2_rtr.get_load_balancer_id())
            """ :type: midonetclient.load_balancer.LoadBalancer"""

            new_rtr.load_balancer_id(lb_obj.get_id()).update()

            pool_obj = (lb_obj.add_pool()
                        .lb_method("ROUND_ROBIN")
                        .protocol("TCP")
                        .create())
            """ :type: midonetclient.pool.Pool"""

            (pool_obj.add_pool_member()
             .address(g1.ip)
             .protocol_port(5081)
             .create())
            (pool_obj.add_pool_member()
             .address(g2.ip)
             .protocol_port(5081)
             .create())
            (pool_obj.add_vip()
             .address("200.200.0.59")
             .protocol_port(5081)
             .create())

            pool2_obj = (lb2_obj.add_pool()
                         .lb_method("ROUND_ROBIN")
                         .protocol("TCP")
                         .create())
            """ :type: midonetclient.pool.Pool"""

            (pool2_obj.add_pool_member()
             .address(g2.ip)
             .protocol_port(5082)
             .create())
            (pool2_obj.add_vip()
             .address("200.200.0.61")
             .protocol_port(5082)
             .create())

            new_chain_obj = (api.add_chain()
                             .tenant_id('admin')
                             .name("test_chain")
                             .create())
            """ :type: midonetclient.chain.Chain"""

            new_chain2_obj = (api.add_chain()
                              .tenant_id('admin')
                              .name("test2_chain")
                              .create())
            """ :type: midonetclient.chain.Chain"""

            rule1 = new_chain2_obj.add_rule().type("accept").create()
            rule2 = new_chain_obj.add_rule().type("accept").create()
            rule3 = new_chain_obj.add_rule().type("jump").create()

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
