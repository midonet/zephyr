__author__ = 'micucci'

import unittest
from PTM.MapConfigReader import MapConfigReader
from PTM.PhysicalTopologyConfig import *
class MapConfigReaderTest(unittest.TestCase):

    def test_read_bridges(self):
        cfg_map = {
            "bridges": [{"name": "br0", "host": "host1", "ip_list": [{"ip": "10.0.0.240", "subnet": "24"}],
                         "options": "stp"}],
            "computes": [], "vlans": [], "hosts": [], "hosted_vms": [], 
            "routers": [], "cassandras": [], "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.bridge_config), 1)
        self.assertEqual(ptc.bridge_config[0].host, 'host1')
        self.assertEqual(ptc.bridge_config[0].name, 'br0')
        self.assertEqual(ptc.bridge_config[0].options, 'stp')
        self.assertEqual(len(ptc.bridge_config[0].ip_list), 1)
        self.assertEqual(ptc.bridge_config[0].ip_list[0].ip_address, "10.0.0.240")
        self.assertEqual(ptc.bridge_config[0].ip_list[0].subnet_mask, "24")

    def test_read_computes(self):
        cfg_map = {
            "bridges": [],
            "computes": [{"interface_list": [{"bridge_link": {"name": "br0"}, "name": "eth0", 
                                              "ip_list": [{"ip": "10.0.0.8", "subnet": "24"}]}],
                          "name": "cmp1"},
                         {"interface_list": [{"name": "eth1",
                                              "ip_list": [{"ip": "10.0.0.8", "subnet": "24"}]}],
                          "name": "cmp2"}],
            "vlans": [], "hosts": [], "hosted_vms": [], "routers": [], "cassandras": [], "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.compute_config), 2)
        self.assertEqual(ptc.compute_config[0].name, "cmp1")
        self.assertEqual(ptc.compute_config[1].name, "cmp2")
        self.assertEqual(ptc.compute_config[0].options, "")
        self.assertEqual(ptc.compute_config[1].options, "")
        self.assertEqual(len(ptc.compute_config[0].interface_list), 1)
        self.assertEqual(len(ptc.compute_config[1].interface_list), 1)
        self.assertNotEqual(ptc.compute_config[0].interface_list[0].bridge_link, None)
        self.assertEqual(ptc.compute_config[0].interface_list[0].bridge_link.name, "br0")
        self.assertEqual(ptc.compute_config[1].interface_list[0].bridge_link, None)

    def test_read_vlans(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": 
                [{"host_list": [
                    {"interface_list": [
                        {"name": "eth0", "ip_list": [{"ip": "172.16.0.224", "subnet": "24"}]},
                        {"name": "eth1", "ip_list": [{"ip": "172.16.0.223", "subnet": "24"}]}],
                     "name": "v1.1"}, 
                    {"interface_list": [
                        {"name": "eth0", "ip_list": [{"ip": "172.16.0.225", "subnet": "24"}]}], 
                     "name": "v2.1"}], 
                  "vlan_id": "1"}],
            "hosts": [],
            "hosted_vms": [],
            "routers": [],
            "cassandras": [],
            "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.vlan_config), 1)
        self.assertEqual(ptc.vlan_config[0].vlan_id, "1")
        self.assertEqual(len(ptc.vlan_config[0].host_list), 2)
        self.assertEqual(ptc.vlan_config[0].host_list[0].name, "v1.1")
        self.assertEqual(ptc.vlan_config[0].host_list[1].name, "v2.1")
        self.assertEqual(len(ptc.vlan_config[0].host_list[0].interface_list), 2)
        self.assertEqual(len(ptc.vlan_config[0].host_list[1].interface_list), 1)
        self.assertEqual(ptc.vlan_config[0].host_list[0].interface_list[0].name, "eth0")
        self.assertEqual(ptc.vlan_config[0].host_list[0].interface_list[1].name, "eth1")
        self.assertEqual(ptc.vlan_config[0].host_list[1].interface_list[0].name, "eth0")

    def test_read_hosts(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": [],
            "hosts": [{"name": "v1.1", "interface_list": [{"bridge_link": {"name": "brv0"}, "name": "eth0"}]},
                      {"name": "v1.2", "interface_list": [{"bridge_link": {"name": "brv0"}, "name": "eth0"}]}],
            "hosted_vms": [],
            "routers": [],
            "cassandras": [],
            "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.host_config), 2)
        self.assertEqual(ptc.host_config[0].name, "v1.1")
        self.assertEqual(ptc.host_config[1].name, "v1.2")
        self.assertEqual(len(ptc.host_config[0].interface_list), 1)
        self.assertEqual(len(ptc.host_config[1].interface_list), 1)
        self.assertEqual(ptc.host_config[0].interface_list[0].name, "eth0")
        self.assertEqual(ptc.host_config[1].interface_list[0].name, "eth0")

    def test_read_vms(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": [],
            "hosts": [],
            "hosted_vms": [],
            "routers": [],
            "cassandras": [],
            "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(True, True)

    def test_read_routers(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": [],
            "hosts": [],
            "hosted_vms": [],
            "routers": [
                {"peer_interface_list": [
                    {"interface_name": "eth0", 
                     "target_host": "cmp1", 
                     "target_interface": {"name": "eth1", "ip_list": [{"ip": "10.0.1.240", "subnet": "16"}]}},
                    {"interface_name": "eth1",
                     "target_host": "cmp2",
                     "target_interface": {"name": "eth1", "ip_list": [{"ip": "10.0.1.240", "subnet": "16"}]}}],
                 "name": "quagga"}],
            "cassandras": [],
            "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.router_config), 1)
        self.assertEqual(ptc.router_config[0].name, 'quagga')
        self.assertEqual(len(ptc.router_config[0].peer_interface_list), 2)
        self.assertEqual(ptc.router_config[0].peer_interface_list[0].interface_name, "eth0")
        self.assertEqual(ptc.router_config[0].peer_interface_list[1].interface_name, "eth1")
        self.assertEqual(ptc.router_config[0].peer_interface_list[0].target_host, "cmp1")
        self.assertEqual(ptc.router_config[0].peer_interface_list[1].target_host, "cmp2")
        self.assertEqual(ptc.router_config[0].peer_interface_list[0].target_interface.name, "eth1")
        self.assertEqual(ptc.router_config[0].peer_interface_list[1].target_interface.name, "eth1")

    def test_read_cassandra(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": [],
            "hosts": [],
            "hosted_vms": [],
            "routers": [],
            "cassandras": [{
                "interface_list": [{"bridge_link": {"name": "br0"}, "name": "eth0",
                                    "ip_list": [{"ip": "10.0.0.5", "subnet": "24"}]}],
                "name": "cass1", "options": "56713727820156410577229101238628035242"}],
            "zookeepers": []
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.cassandra_config), 1)
        self.assertEqual(ptc.cassandra_config[0].name, "cass1")
        self.assertEqual(ptc.cassandra_config[0].options, "56713727820156410577229101238628035242")
        self.assertEqual(len(ptc.cassandra_config[0].interface_list), 1)

    def test_read_zookeeper(self):
        cfg_map = {
            "bridges": [],
            "computes": [],
            "vlans": [],
            "hosts": [],
            "hosted_vms": [],
            "routers": [],
            "cassandras": [],
            "zookeepers": [{
                "interface_list": [{"bridge_link": {"name": "br0"}, "name": "eth0", 
                                    "ip_list": [{"ip": "10.0.0.2", "subnet": "24"}]}],
                "name": "zoo1"}]
        }
        mcr = MapConfigReader()

        ptc = mcr.get_physical_topology_config(cfg_map)
        self.assertEqual(len(ptc.zookeeper_config), 1)
        self.assertEqual(ptc.zookeeper_config[0].name, "zoo1")
        self.assertEqual(ptc.zookeeper_config[0].options, "")
        self.assertEqual(len(ptc.zookeeper_config[0].interface_list), 1)


if __name__ == '__main__':
    unittest.main()
