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
import logging
import neutronclient.v2_0.client as neutron_client

from zephyr.common.cli import LinuxCLI

NetData = namedtuple('NetData', 'network subnet')
RouterData = namedtuple('RouterData', 'router if_list')
BasicTopoData = namedtuple('BasicTopoData', 'main_net pub_net router')


def create_neutron_client(api_version='2.0',
                          endpoint_url='http://localhost:9696',
                          auth_strategy='noauth', tenant_name='admin',
                          token='cat', **kwargs):
    import neutronclient.neutron.client
    client = neutronclient.neutron.client.Client(
        api_version, endpoint_url=endpoint_url,
        auth_strategy=auth_strategy,
        token=token, tenant_name=tenant_name, **kwargs)
    """ :type: neutronclient.v2_0.client.Client"""
    return client


def setup_neutron(api, tenant_id='admin', log=None):
    """
    Creates a network named 'main' in the 'admin' tenant and creates a
    single subnet 'main_sub' with the given IP network.
    :type api: neutron_client.Client
    :type main_name: str
    :type main_subnet_cidr: str
    :type pub_name: str
    :type pub_subnet_cidr: str
    :type tenant_id: str
    :type log: logging.Logger
    :return:
    """
    if log is None:
        log = logging.getLogger('neutron-api-null-logger')
        log.addHandler(logging.NullHandler())

    api.update_quota(tenant_id, {'quota': {'network': -1,
                                           'subnet': -1,
                                           'router': -1,
                                           'pool': -1,
                                           'security_group': -1,
                                           'vip': -1}})


def clean_neutron(log=None):
    """
    Deletes the network named 'main' in the 'admin' tenant along with the
    subnet. Deletes the default secutiry group.
    :type log: logging.Logger
    :return:
    """

    log.debug('Clearing neutron database')
    cli = LinuxCLI(log_cmd=True)
    cmdout = cli.cmd(
        r"neutron-db-manage current 2>&1 | grep '(.*)' | "
        r"awk '{ print $2 }' | sed 's/(\(.*\))/\1/g'")
    log.debug(
        'neutron-db-manage-current out: ' +
        cmdout.stdout + '/' + cmdout.stderr)
    current_neutron_db = cmdout.stdout.strip().split()[0]
    cmdout = cli.cmd(r"midonet-db-manage current 2>&1 | grep '(.*)' | "
                     r"awk '{ print $2 }' | sed 's/(\(.*\))/\1/g'")
    log.debug(
        'midoent-db-manage-current out: ' +
        cmdout.stdout + '/' + cmdout.stderr)
    current_midonet_db = cmdout.stdout.strip()
    cli.cmd(
        'mysql -u root --password=cat neutron -e "DROP DATABASE neutron"')
    log.debug('Re-creating clean neutron database')
    cli.cmd(
        'mysql --user=root --password=cat -e '
        '"CREATE DATABASE IF NOT EXISTS neutron"')
    log.debug(
        'Re-populating neutron and midonet tables '
        'for version (neutron/mn): (' +
        current_neutron_db + '/' + current_midonet_db + ')')
    cli.cmd("neutron-db-manage upgrade " + current_neutron_db)
    cli.cmd("midonet-db-manage upgrade " + current_midonet_db)
    log.debug('Restarting neutron')
    cli.cmd("service neutron-server restart")
    LinuxCLI(priv=False).cmd(
        'for i in `ip netns | grep qdhcp`; do sudo ip netns del $i; done')


def get_neutron_api_url(api):
    """
    :type api: neutronclient.v2_0.client.Client
    """
    return api.httpclient.endpoint_url + '/v' + str(api.version)
