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

import unittest
import os

from common.LogManager import LogManager
from PTM.impl.ConfiguredHostPTMImpl import ConfiguredHostPTMImpl
from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from VTM.VirtualTopologyManager import VirtualTopologyManager
from VTM.NeutronAPI import *
from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone
from PTM.application.Midolman import Midolman


class NeutronAPITest(unittest.TestCase):
    lm = LogManager('test-logs')
    ptm_i = None
    ptm = None
    vtm = None
    api = None
    mn_api = None
    main_network = None
    main_subnet = None
    pub_network = None
    pub_subnet = None

    @classmethod
    def setUpClass(cls):
        cls.ptm_i = ConfiguredHostPTMImpl(root_dir=os.path.dirname(os.path.abspath(__file__)) + '/../..',
                                          log_manager=cls.lm)
        cls.ptm_i.configure_logging(debug=True)
        cls.ptm = PhysicalTopologyManager(cls.ptm_i)
        cls.ptm.configure(os.path.dirname(os.path.abspath(__file__)) + '/test-basic-config.json')
        logging.getLogger("neutronclient").addHandler(logging.StreamHandler())
        try:
            cls.ptm.startup()
            cls.vtm = VirtualTopologyManager(client_api_impl=create_neutron_client(),
                                             physical_topology_manager=cls.ptm)

            cls.api = cls.vtm.get_client()
            """ :type: neutron_client.Client"""

            cls.mn_api = create_midonet_client()

            log = logging.getLogger("neutronclient")
            log.setLevel(logging.DEBUG)

            tunnel_zone_host_map = {}
            for host_name, host in cls.ptm.impl_.hosts_by_name.iteritems():
                # On each host, check if there is at least one Midolman app running
                for app in host.applications:
                    if isinstance(app, Midolman):
                        # If so, add the host and its eth0 interface to the tunnel zone map
                        # and move on to next host
                        tunnel_zone_host_map[host.name] = host.interfaces['eth0'].ip_list[0].ip
                        break

            setup_main_tunnel_zone(cls.mn_api,
                                   tunnel_zone_host_map,
                                   log)

            try:
                btd = setup_neutron(cls.api, log=log)
                cls.main_network = btd.main_net.network
                cls.main_subnet = btd.main_net.subnet
                cls.pub_network = btd.pub_net.network
                cls.pub_subnet = btd.pub_net.subnet
            except Exception:
                clean_neutron(cls.api, log=log)
                raise
        except:
            cls.ptm.shutdown()
            LinuxCLI().cmd('ip netns del vm1')
            raise

    def test_neutron_api_ping_two_hosts_same_hv(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None

        try:
            port1def = {'port': {'name': 'port1',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.main_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.ptm_i.LOG.info("Got port 1 IP: " + str(ip1))
            self.ptm_i.LOG.info("Got port 2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(ip=ip1, mac=port1['mac_address'], hv_host='cmp2')
            vm2 = self.vtm.create_vm(ip=ip2, mac=port2['mac_address'], hv_host='cmp2')

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))
            self.assertTrue(vm2.ping(target_ip=ip1, on_iface='eth0'))

        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])
            if port2 is not None:
                self.api.delete_port(port2['id'])

    def test_neutron_api_ping_two_hosts_diff_hv(self):
        port1 = None
        port2 = None
        vm1 = None
        vm2 = None

        try:
            port1def = {'port': {'name': 'port1',
                                 'network_id': self.pub_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port1 = self.api.create_port(port1def)['port']
            ip1 = port1['fixed_ips'][0]['ip_address']

            port2def = {'port': {'name': 'port2',
                                 'network_id': self.pub_network['id'],
                                 'admin_state_up': True,
                                 'tenant_id': 'admin'}}
            port2 = self.api.create_port(port2def)['port']
            ip2 = port2['fixed_ips'][0]['ip_address']

            self.ptm_i.LOG.info("Got port 1 IP: " + str(ip1))
            self.ptm_i.LOG.info("Got port 2 IP: " + str(ip2))

            vm1 = self.vtm.create_vm(ip1, mac=port1['mac_address'], hv_host='cmp1', name='vm1')
            """ :type: Guest"""
            vm2 = self.vtm.create_vm(ip2, mac=port2['mac_address'], hv_host='cmp2', name='vm2')
            """ :type: Guest"""

            vm1.plugin_vm('eth0', port1['id'])
            vm2.plugin_vm('eth0', port2['id'])

            self.assertTrue(vm1.ping(target_ip=ip2, on_iface='eth0'))

        finally:
            if vm1 is not None:
                vm1.terminate()
            if vm2 is not None:
                vm2.terminate()

            if port1 is not None:
                self.api.delete_port(port1['id'])
            if port2 is not None:
                self.api.delete_port(port2['id'])

    @classmethod
    def tearDownClass(cls):
        log = logging.getLogger("neutronclient")
        log.setLevel(logging.DEBUG)

        try:
            cls.ptm.shutdown()
            LinuxCLI().cmd('ip netns del vm1')
        finally:
            clean_neutron(cls.api, log=log)


from CBT.UnitTestRunner import run_unit_test
run_unit_test(NeutronAPITest)
