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

# Topology Grammar (pseudo-BNF) for JSON/YAML/etc.
#
# IP := ( ip, subnet )
# IPDefList := [ IPDef1, ..., IPDefN ]
# BridgeDef := ( name, ip_addresses=IPDefList, mac_address, options )
# BridgeDefList := [ BridgeDef1, ..., BridgeDefN ]
# VLANDef := ( id, ip_addresses=IPDefList )
# VLANDefList := [ VLANDef1, ..., VLANDefN ]
# InterfaceDef := ( name, ip_addresses=IPDefList, mac_address, linked_bridge, vlans=VLANDefList )
# InterfaceDefList := [ InterfaceDef1, ..., InterfaceDefN ]
# HostDef := { name, bridges=BridgeDefList, interfaces=InterfaceDefList }
# HostDefList := [ HostDef1, ..., HostDefN ]
# HostInterfaceDef := { host, interface }
# WiringDef := { near=HostInterfaceDef, far=HostInterfaceDef }
# WiringDefList := [ WiringDef1, ..., WiringDefN ]
# ApplicationDef := { class, ... }
# ImplementationDef := { impl, [ ApplicationDef1, ..., ApplicationDefN ] }
# ImplementationDefList := [ ImplementationDef1, ..., ImplementationDefN ]

# PhysicalTopologyConfig :=
#    { 'hosts'=HostDefMap, 'wiring'=WiringDefMap, 'implementation'=ImplementationDefMap }

from common.Exceptions import *
from common.IP import IP


class BridgeDef(object):
    def __init__(self, name, ip_addresses=None, mac_address=None, options=None):
        """
        :type name: str
        :type ip_addresses: list[IP]
        :type mac_address: str
        :type options: list[str]
        """
        self.name = name
        self.ip_addresses = ip_addresses
        self.mac_address = mac_address
        self.options = options

    @staticmethod
    def make_bridge(br_cfg):
        if 'name' not in br_cfg:
            raise ObjectNotFoundException('"name" field required for bridge definition')
        name = br_cfg['name']
        ip_addresses = []
        mac_address = br_cfg['mac_address'] if 'mac_address' in br_cfg else None
        options = br_cfg['options'].split() if 'options' in br_cfg else None

        for ip in br_cfg['ip_addresses'] if 'ip_addresses' in br_cfg else []:
            ip_addresses.append(IP(**ip))

        return BridgeDef(name, ip_addresses, mac_address, options)


class VLANDef(object):
    def __init__(self, vlan_id, ip_addresses=None):
        """
        :type vlan_id: str
        :type ip_addresses: list[IP]
        """
        self.vlan_id = vlan_id
        self.ip_addresses = ip_addresses

    @staticmethod
    def make_vlan(vlan_cfg):
        if 'id' not in vlan_cfg:
            raise ObjectNotFoundException('"id" field required for VLAN definition')
        id = vlan_cfg['id']
        ip_addresses = []

        for ip in vlan_cfg['ip_addresses'] if 'ip_addresses' in vlan_cfg else []:
            ip_addresses.append(IP(**ip))

        return VLANDef(id, ip_addresses)


class InterfaceDef(object):
    def __init__(self, name, ip_addresses=None, mac_address=None, linked_bridge=None, vlans=None):
        """
        :type name: str
        :type ip_addresses: list[IP]
        :type mac_address: str
        :type linked_bridge: str
        :type vlans: dict[str, list[IP]]
        """
        self.name = name
        self.ip_addresses = ip_addresses
        self.mac_address = mac_address
        self.linked_bridge = linked_bridge
        self.vlans = vlans

    @staticmethod
    def make_interface(if_cfg):
        if 'name' not in if_cfg:
            raise ObjectNotFoundException('"name" field required for interface definition')
        name = if_cfg['name']
        ip_addresses = []
        mac_address = if_cfg['mac_address'] if 'mac_address' in if_cfg else None
        linked_bridge = if_cfg['linked_bridge'] if 'linked_bridge' in if_cfg else None
        vlans = {}

        for ip in if_cfg['ip_addresses'] if 'ip_addresses' in if_cfg else []:
            ip_addresses.append(IP(**ip))

        for vlan in if_cfg['vlans'] if 'vlans' in if_cfg else []:
            new_vlan = VLANDef.make_vlan(vlan)
            vlans[new_vlan.vlan_id] = new_vlan.ip_addresses

        return InterfaceDef(name, ip_addresses, mac_address, linked_bridge, vlans)


class IPForwardRuleDef(object):
    def __init__(self, exterior=None, interior=None):
        """
        :type exterior: str
        :type interior: str
        """
        self.exterior = exterior
        self.interior = interior

    @staticmethod
    def make_ip_forward_rule(if_cfg):
        if 'exterior' not in if_cfg:
            raise ObjectNotFoundException('"exterior" field required for interface definition')
        exterior = if_cfg['exterior']
        if 'interior' not in if_cfg:
            raise ObjectNotFoundException('"interior" field required for interface definition')
        interior = if_cfg['interior']

        return IPForwardRuleDef(exterior, interior)


class RouteRuleDef(object):
    def __init__(self, dest=None, gw=None, dev=None):
        """
        :type dest: IP
        :type gw: IP
        :type dev: str
        """
        self.dest = dest
        self.gw = gw
        self.dev = dev

    @staticmethod
    def make_route_rule(if_cfg):
        if 'dest' not in if_cfg:
            raise ObjectNotFoundException('"dest" field required for route definition')
        dest = if_cfg['dest']
        gw = IP.make_ip(if_cfg['gw']) if 'gw' in if_cfg else None
        dev = if_cfg['dev'] if 'dev' in if_cfg else None
        dest_ip = IP.make_ip('0.0.0.0/0' if dest == 'default' else dest)
        return RouteRuleDef(dest_ip, gw, dev)


class HostDef(object):
    def __init__(self, name, bridges=None, interfaces=None, ip_forward_rules=None, route_rules=None):
        """
        :type name: str
        :type bridges: dict[str, BridgeDef]
        :type interfaces: dict[str, InterfaceDef]
        :type ip_forward_rules: list[IPForwardRuleDef]
        :type route_rules: list[str, RouteRuleDef]
        """
        self.name = name
        self.bridges = bridges
        self.interfaces = interfaces
        self.ip_forward_rules = ip_forward_rules
        self.route_rules = route_rules

    @staticmethod
    def make_host(host_cfg):
        if 'name' not in host_cfg:
            raise ObjectNotFoundException('"name" field required for host definition')
        name = host_cfg['name']
        bridges = {}
        interfaces = {}
        ip_forward_rules = []
        route_rules = []

        for br_cfg in host_cfg['bridges'] if 'bridges' in host_cfg else []:
            new_br = BridgeDef.make_bridge(br_cfg)
            bridges[new_br.name] = new_br
        for if_cfg in host_cfg['interfaces'] if 'interfaces' in host_cfg else []:
            new_if = InterfaceDef.make_interface(if_cfg)
            interfaces[new_if.name] = new_if
        for ip_rule_cfg in host_cfg['ip_forward'] if 'ip_forward' in host_cfg else []:
            new_rule = IPForwardRuleDef.make_ip_forward_rule(ip_rule_cfg)
            ip_forward_rules.append(new_rule)
        for route_cfg in host_cfg['routes'] if 'routes' in host_cfg else []:
            new_rule = RouteRuleDef.make_route_rule(route_cfg)
            route_rules.append(new_rule)

        return HostDef(name, bridges, interfaces, ip_forward_rules, route_rules)


class HostInterfaceDef(object):
    def __init__(self, host, interface):
        """
        :type host: str
        :type interface: str
        """
        self.host = host
        self.interface = interface

    @staticmethod
    def make_host_interface(hi_cfg):
        if 'host' not in hi_cfg:
            raise ObjectNotFoundException('"host" field required for host-interface definition')
        if 'interface' not in hi_cfg:
            raise ObjectNotFoundException('"interface" field required for host-interface definition')
        return HostInterfaceDef(hi_cfg['host'], hi_cfg['interface'])


class WiringDef(object):
    def __init__(self, near, far):
        """
        :type near: HostInterfaceDef
        :type far: HostInterfaceDef
        """
        self.near = near
        self.far = far

    @staticmethod
    def make_wiring(wire_cfg):
        if 'near' not in wire_cfg:
            raise ObjectNotFoundException('"near" field required for wiring definition')
        if 'far' not in wire_cfg:
            raise ObjectNotFoundException('"far" field required for wiring definition')

        near = HostInterfaceDef.make_host_interface(wire_cfg['near'])
        far = HostInterfaceDef.make_host_interface(wire_cfg['far'])

        return WiringDef(near, far)


class ApplicationDef(object):
    def __init__(self, class_name, **kwargs):
        self.class_name = class_name
        self.kwargs = kwargs

    @staticmethod
    def make_application(app_cfg):
        if 'class' not in app_cfg:
            raise ObjectNotFoundException('"class" field required for application definition')

        return ApplicationDef(app_cfg['class'], **{k: app_cfg[k] for k in app_cfg.keys() if k != 'class'})


class ImplementationDef(object):
    def __init__(self, host, impl, apps):
        """
        :type host: str
        :type impl: str
        :type apps: list[ApplicationDef]
        """
        self.host = host
        self.impl = impl
        self.apps = apps

    @staticmethod
    def make_implementation(impl_cfg):
        if 'host' not in impl_cfg:
            raise ObjectNotFoundException('"host" field required for implementation definition')
        if 'impl' not in impl_cfg:
            raise ObjectNotFoundException('"impl" field required for implementation definition')

        host = impl_cfg['host']
        impl = impl_cfg['impl']

        apps = []
        for app_cfg in impl_cfg['apps'] if 'apps' in impl_cfg else []:
            new_app = ApplicationDef.make_application(app_cfg)
            apps.append(new_app)

        return ImplementationDef(host, impl, apps)


class WireConnectionDef(object):
    def __init__(self, host, interface):
        """
        :type host: str
        :type interface: InterfaceDef
        """
        self.host = host
        self.interface = interface


class PhysicalTopologyConfig(object):
    def __init__(self, hosts=None, wiring=None, implementation=None, host_start_order=None):
        """
        :type hosts: dict[str, HostDef]
        :type wiring: dict[str, dict[str, HostInterfaceDef]]
        :type implementation: dict[str, ImplementationDef]
        :type host_start_order: list[str|list[str]]
        """
        self.hosts = hosts
        self.wiring = wiring
        self.implementation = implementation
        self.host_start_order = host_start_order

    @staticmethod
    def make_physical_topology(ptm_cfg):
        if 'root_server_host' not in ptm_cfg:
            raise ObjectNotFoundException('"root_server_host" field required for topology definition')
        root_server_host = ptm_cfg['root_server_host']
        hosts = {}
        wiring = {}
        implementation = {}
        host_start_order = []

        for host_cfg in ptm_cfg['hosts'] if 'hosts' in ptm_cfg else []:
            host = HostDef.make_host(host_cfg)
            hosts[host.name] = host

        for wiring_cfg in ptm_cfg['wiring'] if 'wiring' in ptm_cfg else []:
            wire = WiringDef.make_wiring(wiring_cfg)
            if wire.near.host not in wiring:
                wiring[wire.near.host] = {}

            wiring[wire.near.host][wire.near.interface] = wire.far

        for imp_cfg in ptm_cfg['implementation'] if 'implementation' in ptm_cfg else []:
            imp = ImplementationDef.make_implementation(imp_cfg)
            implementation[imp.host] = imp

        for host_name in ptm_cfg['host_start_order'] if 'host_start_order' in ptm_cfg else []:
            host_start_order.append(host_name)

        return PhysicalTopologyConfig(hosts, wiring, implementation, host_start_order)
