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

from common.CLI import LinuxCLI

import logging

import neutronclient.v2_0.client as neutron_client

def create_neutron_client(api_version='2.0', endpoint_url='http://localhost:9696',
                          auth_strategy='noauth', tenant_name='admin', token='cat', **kwargs):
    import neutronclient.neutron.client
    return neutronclient.neutron.client.Client(api_version, endpoint_url=endpoint_url,
                                               auth_strategy=auth_strategy,
                                               token=token, tenant_name=tenant_name, **kwargs)


def setup_neutron(api, subnet_cidr='192.168.0.0/24', pubsubnet_cidr='200.200.0.0/24', log=None):
    """
    Creates a network named 'main' in the 'admin' tenant and creates a single subnet 'main_sub'
    with the given IP network.
    :type api: neutron_client.Client
    :type subnet_cidr: str
    :type log: logging.Logger
    :return:
    """
    if log is None:
        log = logging.getLogger('neutron-api-null-logger')
        log.addHandler(logging.NullHandler())

    # Create main network
    tenant_id = 'admin'
    networks = api.list_networks(name='main')
    if len(networks['networks']) == 0:
        network_resp = api.create_network({'network': {'name': 'main', 'admin_state_up': True,
                                                       'tenant_id': tenant_id}})
        main_network = network_resp['network']
    else:
        main_network = networks['networks'][0]
    log.debug('Using main network: ' + str(main_network))

    # Create main network's subnet
    subnets = api.list_subnets(name='main_sub', network_id=main_network['id'])
    if len(subnets['subnets']) == 0:
        subnet_resp = api.create_subnet({'subnet': {'name': 'main_sub',
                                                    'network_id': main_network['id'],
                                                    'ip_version': 4, 'cidr': subnet_cidr,
                                                    'tenant_id': tenant_id}})
        main_subnet = subnet_resp['subnet']
    else:
        main_subnet = subnets['subnets'][0]
    log.debug('Using main subnet: ' + str(main_subnet))

    # Create a public network for use with edge routing (if needed
    pub_network = api.create_network({'network': {'name': 'public',
                                                  'admin_state_up': True,
                                                  'router:external': True,
                                                  'tenant_id': 'admin'}})['network']
    log.debug('Using public network: ' + str(pub_network))

    # Create public network's subnet
    pub_subnet = api.create_subnet({'subnet': {'name': 'pub_sub',
                                               'network_id': pub_network['id'],
                                               'ip_version': 4,
                                               'cidr': pubsubnet_cidr,
                                               'tenant_id': 'admin'}})['subnet']
    log.debug('Using public subnet: ' + str(pub_subnet))
    public_router = api.create_router({'router': {'name': 'pub_main_router',
                                                  'admin_state_up': True,
                                                  'external_gateway_info': {
                                                      "network_id": pub_network['id']
                                                  },
                                                  'tenant_id': 'admin'}})['router']

    # Route traffic between main subnet and public gateway
    api.add_interface_router(public_router['id'], {'subnet_id': main_subnet['id']})

    # Create default security group
    default_secgroups = api.list_security_groups(name='default')['security_groups']
    if len(default_secgroups) == 0:
        log.debug('Creating default sec group: ')
        def_sg = api.create_security_group({'security_group': {'name': 'default',
                                                               'tenant_id': tenant_id}})
        def_sg_id = def_sg['security_group']['id']
    else:
        def_sg_id = default_secgroups[0]['id']

    # Add rules to default security group
    log.debug('Creating default sec group rules for sec group: ' + def_sg_id)
    api.create_security_group_rule({'security_group_rule': {'direction': 'ingress', 'protocol': 'icmp',
                                                            'security_group_id': def_sg_id, 'tenant_id': tenant_id}})
    api.create_security_group_rule({'security_group_rule': {'direction': 'egress', 'protocol': 'icmp',
                                                            'security_group_id': def_sg_id, 'tenant_id': tenant_id}})
    api.create_security_group_rule({'security_group_rule': {'direction': 'ingress', 'protocol': 'tcp',
                                                            'security_group_id': def_sg_id, 'tenant_id': tenant_id}})
    api.create_security_group_rule({'security_group_rule': {'direction': 'egress', 'protocol': 'tcp',
                                                            'security_group_id': def_sg_id, 'tenant_id': tenant_id}})

    return main_network, main_subnet, pub_network, pub_subnet


def clean_neutron(api, log=None):
    """
    Deletes the network named 'main' in the 'admin' tenant along with the subnet. Deletes the
    default secutiry group.
    :type api: neutron_client.Client
    :type log: logging.Logger
    :return:
    """

    log.debug('Clearing neutron database')
    cli = LinuxCLI(log_cmd=True)
    current_neutron_db = cli.cmd(r"neutron-db-manage current 2>&1 | grep '(.*)' | "
                                 r"awk '{ print $2 }' | sed 's/(\(.*\))/\1/g'").stdout.strip()
    current_midonet_db = cli.cmd(r"midonet-db-manage current 2>&1 | grep '(.*)' | "
                                 r"awk '{ print $2 }' | sed 's/(\(.*\))/\1/g'").stdout.strip()
    cli.cmd('mysql -u root --password=cat neutron -e "DROP DATABASE neutron"')
    log.debug('Re-creating clean neutron database')
    cli.cmd('mysql --user=root --password=cat -e "CREATE DATABASE IF NOT EXISTS neutron"')
    log.debug('Re-populating neutron and midonet tables for version (neutron/mn): (' +
              current_neutron_db + '/' + current_midonet_db + ')')
    cli.cmd("neutron-db-manage upgrade " + current_neutron_db)
    cli.cmd("midonet-db-manage upgrade " + current_midonet_db)
    log.debug('Restarting neutron')
    cli.cmd("service neutron-server restart")
    LinuxCLI(priv=False).cmd('for i in `ip netns | grep qdhcp`; do sudo ip netns del $i; done')
