__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Topology Grammar (pseudo-BNF)
#
# 'ip' = IPDef := ( ip_address, subnet_mask )
# 'ip_list' = IPDefList := [ IPDef1, ..., IPDefN ]
# 'bridge_link' = BridgeLinkDef := ( host, name )
# 'bridge' = BridgeDef := ( name, host, IPDefList, options )
# 'bridge_list' = BridgeDefList := [ BridgeDef1, ..., BridgeDefN ]
# 'interface' = InterfaceDef := ( name, IPDefList, BridgeLinkDef )
# 'interface_list' = InterfaceDefList := [ InterfaceDef1, ..., InterfaceDefN ]
# 'host' = HostDef := { name, InterfaceDefList, options }
# 'host_list' = HostDefList := [ HostDef1, ..., HostDefN ]
# 'zookeeper_list' = ZookeeperDefList = HostDefList
# 'cassandra_list' = CassandraDefList = HostDefList
# 'compute_list' = ComputeDefList = HostDefList
# 'vm' = VMDef = ( hypervisor_host, HostDef )
# 'vm_list' = VMDefList = [ VMDef1, ..., VMDefN ]
# 'peer_interface' = PeerInterfaceDef := ( near_interface_name, target_host, InterfaceDef )
# 'peer_interface_list' = PeerInterfaceDefList := [ PeerInterfaceDef1, ..., PeerInterfaceDefN ]
# 'router' = RouterDef := ( name, PeerInterfaceDefList )
# 'router_list' = RouterDefList := [ RouterDef1, ..,, RouterDefN ]
# 'vlan' = VLANDef := ( vlan_id, HostDefList )
# 'vlan_list' = VLANDefList := [ VLANDef1, ..., VLANDefN ]
# PhysicalTopologyConfig := 
#    { 'bridge_config'=BridgeDefList, 'zookeeper_config'=ZookeeperDefList, 'cassandra_config'=CassandraDefList,
#      'compute_config'=ComputeDefList, 'router_config'=RouterDefList, 'vm_config'=VMDefList,
#      'vlan_config'=VLANDefList, 'hosts'=HostList }


class IPDef(object):
    def __init__(self, ip_address, subnet_mask='24'):
        """
        :type ip_address: str
        :type subnet_mask: str
        """
        self.ip_address = ip_address
        self.subnet_mask = subnet_mask
    def __repr__(self):
        return self.ip_address + "/" + self.subnet_mask


class BridgeLinkDef(object):
    def __init__(self, host='', name=''):
        """
        :type host: str
        :type name: str
        """
        self.host = host
        self.name = name


class BridgeDef(object):
    def __init__(self, name, host='', ip_list=list(), options=''):
        """
        :type name: str
        :type host: str
        :type ip_list: list[IPDef]
        :type options: str
        """
        self.name = name
        self.host = host
        self.ip_list = ip_list
        self.options = options

class InterfaceDef(object):
    def __init__(self, name, bridge_link=None, ip_list=list(), mac_address='default'):
        """
        :type name: str
        :type bridge_link: BridgeLinkDef
        :type ip_list: list[IPDef]
        :type mac_address: str
        """
        self.name = name
        self.ip_list = ip_list
        self.bridge_link = bridge_link
        self.mac_address = mac_address


class HostDef(object):
    def __init__(self, name, interface_list=list(), options=''):
        """
        :type name: str
        :type interface_list: list[InterfaceDef]
        :type options: str
        """
        self.name = name
        self.interface_list = interface_list
        self.options = options


class VMDef(object):
    def __init__(self, hypervisor_host_name, vm_host):
        """
        :type hypervisor_host_name: str
        :type vm_host: HostDef
        """
        self.hypervisor_host_name = hypervisor_host_name
        self.vm_host = vm_host


class PeerInterfaceDef(object):
    def __init__(self, interface_name, target_host, target_interface):
        """
        :type interface_name: str
        :type target_host: str
        :type target_interface: InterfaceDef
        """
        self.interface_name = interface_name
        self.target_host = target_host
        self.target_interface = target_interface


class RouterDef(object):
    def __init__(self, name, peer_interface_list=list()):
        """
        :type name: str
        :type peer_interface_list: list[PeerInterfaceDef]
        """
        self.name = name
        self.peer_interface_list = peer_interface_list


class VLANDef(object):
    def __init__(self, vlan_id, host_list=list()):
        """
        :type vlan_id: str
        :type host_list: list[HostDef]
        """
        self.vlan_id = vlan_id
        self.host_list = host_list


class PhysicalTopologyConfig(object):
    def __init__(self):
        self.bridge_config = []
        """ :type: list[BridgeDef]"""
        self.zookeeper_config = []
        """ :type: list[HostDef]"""
        self.cassandra_config = []
        """ :type: list[HostDef]"""
        self.compute_config = []
        """ :type: list[HostDef]"""
        self.router_config = []
        """ :type: list[RouterDef]"""
        self.host_config = []
        """ :type: list[HostDef]"""
        self.vm_config = []
        """ :type: list[VMDef]"""
        self.vlan_config = []
        """ :type: list[VLANDef]"""

    def add_bridge_def(self, bridge):
        """ :type bridge: BridgeDef """
        self.bridge_config.append(bridge)

    def add_zookeeper_def(self, zookeeper):
        """ :type zookeeper: HostDef """
        self.zookeeper_config.append(zookeeper)

    def add_cassandra_def(self, cassandra):
        """ :type cassandra: HostDef """
        self.cassandra_config.append(cassandra)

    def add_compute_def(self, compute):
        """ :type compute: HostDef """
        self.compute_config.append(compute)

    def add_router_def(self, router):
        """ :type router: RouterDef """
        self.router_config.append(router)

    def add_host_def(self, host):
        """ :type host: HostDef """
        self.host_config.append(host)

    def add_vm_def(self, vm):
        """ :type vm: VMDef """
        self.vm_config.append(vm)

    def add_vlan_def(self, vlan):
        """ :type vlan: VLANDef """
        self.vlan_config.append(vlan)
