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

import PhysicalTopologyConfig
from common.Exceptions import *

class ConfigReader(object):
    def __init__(self):
        pass


def get_val_from_map(src_map, desired_key, required=False, default=None):
    if src_map is not None and desired_key in src_map:
        return src_map[desired_key]
    if required is True:
        raise ArgMismatchException(desired_key)
    return default


def get_list_from_map(src_map, desired_key, required=False, default=list()):
    if src_map is not None and desired_key in src_map:
        return [x for x in src_map[desired_key]]
    if required is True:
        raise ArgMismatchException(desired_key)
    return default


def get_translation_from_map(func, src_map, desired_key, required=False, default=None):
    if src_map is not None and desired_key in src_map:
        return func(src_map[desired_key])
    if required is True:
        raise ArgMismatchException(desired_key)
    return default


def get_list_translation_from_map(func, src_map, desired_key, required=False, default=list()):
    if src_map is not None and desired_key in src_map:
        return [func(x) for x in src_map[desired_key]]
    if required is True:
        raise ArgMismatchException(desired_key)
    return default


def make_ip_def_from_config_object(cfg_obj):
    ip = get_val_from_map(cfg_obj, 'ip', True)
    subnet = get_val_from_map(cfg_obj, 'subnet', False, '32')
    return PhysicalTopologyConfig.IPDef(ip, subnet)


def make_bridge_link_def_from_config_object(cfg_obj):
    bridge_name = get_val_from_map(cfg_obj, 'name', True)
    bridge_host = get_val_from_map(cfg_obj, 'host', False, '')
    return PhysicalTopologyConfig.BridgeLinkDef(bridge_host, bridge_name)


def make_bridge_def_from_config_object(cfg_obj):
    name = get_val_from_map(cfg_obj, 'name', True)
    host = get_val_from_map(cfg_obj, 'host', False, '')
    ips = get_list_translation_from_map(make_ip_def_from_config_object, cfg_obj, 'ip_list')
    options = get_val_from_map(cfg_obj, 'options', False, '')
    return PhysicalTopologyConfig.BridgeDef(name, host, ips, options)


def make_interface_def_from_config_object(cfg_obj):
    name = get_val_from_map(cfg_obj, 'name', True)
    linked_bridge = get_translation_from_map(make_bridge_link_def_from_config_object, cfg_obj, 'bridge_link')
    ips = get_list_translation_from_map(make_ip_def_from_config_object, cfg_obj, 'ip_list')
    mac = get_val_from_map(cfg_obj, 'mac_address', False, 'default')
    return PhysicalTopologyConfig.InterfaceDef(name, linked_bridge, ips, mac)


def make_host_def_from_config_object(cfg_obj):
    name = get_val_from_map(cfg_obj, 'name', True)
    interfaces = get_list_translation_from_map(make_interface_def_from_config_object, cfg_obj, 'interface_list')
    options = get_val_from_map(cfg_obj, 'options', False, '')
    return PhysicalTopologyConfig.HostDef(name, interfaces, options)


def make_peer_interface_def_from_config_object(cfg_obj):
    near_if = get_val_from_map(cfg_obj, 'interface_name', required=True)
    target_host = get_val_from_map(cfg_obj, 'target_host', required=True)
    target_if = get_translation_from_map(make_interface_def_from_config_object, cfg_obj, 'target_interface')
    return PhysicalTopologyConfig.PeerInterfaceDef(near_if, target_host, target_if)


def make_router_def_from_config_object(cfg_obj):
    name = get_val_from_map(cfg_obj, 'name', True)
    interfaces = get_list_translation_from_map(make_peer_interface_def_from_config_object, cfg_obj,
                                               'peer_interface_list')
    return PhysicalTopologyConfig.RouterDef(name, interfaces)


def make_vm_def_from_config_object(cfg_obj):
    hv_name = get_val_from_map(cfg_obj, 'hypervisor_host', True)
    vm_info = get_translation_from_map(make_host_def_from_config_object, cfg_obj, 'host')
    return PhysicalTopologyConfig.VMDef(hv_name, vm_info)


def make_vlan_def_from_config_object(cfg_obj):
    vlan_id = get_val_from_map(cfg_obj, 'vlan_id', True)
    hosts = get_list_translation_from_map(make_host_def_from_config_object, cfg_obj, 'host_list')
    return PhysicalTopologyConfig.VLANDef(vlan_id, hosts)


class MapConfigReader(ConfigReader):
    def __init__(self):
        super(MapConfigReader, self).__init__()

    @staticmethod
    def get_physical_topology_config(python_config):
        try:
            pt = PhysicalTopologyConfig.PhysicalTopologyConfig()

            for i in python_config["bridges"]:
                pt.add_bridge_def(make_bridge_def_from_config_object(i))

            for i in python_config["zookeepers"]:
                pt.add_zookeeper_def(make_host_def_from_config_object(i))

            for i in python_config["cassandras"]:
                pt.add_cassandra_def(make_host_def_from_config_object(i))

            for i in python_config["computes"]:
                pt.add_compute_def(make_host_def_from_config_object(i))

            for i in python_config["routers"]:
                pt.add_router_def(make_router_def_from_config_object(i))

            for i in python_config["hosts"]:
                pt.add_host_def(make_host_def_from_config_object(i))

            for i in python_config["hosted_vms"]:
                pt.add_vm_def(make_vm_def_from_config_object(i))

            for i in python_config["vlans"]:
                pt.add_vlan_def(make_vlan_def_from_config_object(i))

            return pt
        except ArgMismatchException as e:
            print 'Configuration error: ' + str(e) + ' is required, but not found in config object'
            raise e
