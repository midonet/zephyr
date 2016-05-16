#!/usr/bin/env python
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

import getopt
import sys
import traceback

from zephyr.common.cli import LinuxCLI
from zephyr.common.exceptions import ArgMismatchException
from zephyr.common.exceptions import ExitCleanException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.exceptions import SubprocessFailedException
from zephyr.common.exceptions import TestException


cli = LinuxCLI(log_cmd=True, print_cmd_out=True)
cli.add_environment_variable("DEBIAN_FRONTEND", "noninteractive")


def usage(except_obj):
    print('Usage: neutron-setup.py -v <OpenStack version>')
    if except_obj is not None:
        raise except_obj


class NeutronComponentInstaller(object):
    def __init__(self, ost_version):
        self.version = ost_version
        self.config_funcs = {'kilo': self.kilo_config,
                             'liberty': self.liberty_config,
                             'mitaka': self.liberty_config}

    def install_packages(self):

        cli.cmd("apt-get install -y python3-software-properties")
        cli.cmd("add-apt-repository -y cloud-archive:" + str(self.version))
        cli.cmd("apt-get update")

        cli.cmd('apt-get install -y mysql-server mysql-client python-mysqldb')

        cli.cmd('mysqladmin -u root password cat')

        cli.regex_file('/etc/mysql/my.cnf',
                       's/.*bind-address.*/bind-address = 127.0.0.1/')
        cli.regex_file('/etc/mysql/my.cnf',
                       's/.*max_connections.*/max_connections = 1024/')
        cli.cmd("service mysql restart")

        if not cli.grep_cmd('dpkg -l', 'rabbitmq-server'):
            cli.cmd('apt-get install -y rabbitmq-server')

        cli.cmd("rabbitmqctl change_password guest cat")
        cli.cmd("service rabbitmq-server restart")

        print(cli.cmd('apt-get install -y neutron-server neutron-dhcp-agent '
                      'python-neutronclient '
                      'python-neutron-lbaas python-mysql.connector').stdout)

    def configure_for_midonet(self, mn_api_url):
        cli.cmd('mysql --user=root --password=cat -e '
                '"DROP DATABASE neutron"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"CREATE DATABASE neutron"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"DROP USER neutron@localhost"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"DROP USER neutron@\'%\'"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"CREATE USER neutron@localhost IDENTIFIED BY \'cat\'"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"CREATE USER neutron@\'%\' IDENTIFIED BY \'cat\'"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"GRANT ALL PRIVILEGES ON neutron.* TO neutron@localhost"')
        cli.cmd('mysql --user=root --password=cat -e '
                '"GRANT ALL PRIVILEGES ON neutron.* TO neutron@\'%\'"')

        config_func = self.config_funcs[str(self.version)]
        config_func(mn_api_url)

        cli.write_to_file('/etc/default/neutron-server',
                          'NEUTRON_PLUGIN_CONFIG="/etc/neutron/plugin.ini"\n')
        cli.cmd('neutron-db-manage --config-file /etc/neutron/neutron.conf '
                '--config-file /etc/neutron/plugin.ini upgrade head')
        if str(self.version) == 'kilo' or str(self.version) == 'liberty':
            cli.cmd('midonet-db-manage upgrade head')
        else:
            cli.cmd('neutron-db-manage --subproject '
                    'networking-midonet upgrade heads')

        cli.cmd("service neutron-server restart")
        cli.cmd("service neutron-dhcp-agent restart")

    @staticmethod
    def kilo_config(mn_api_url):

        cfg_file_str = (
            "[DEFAULT]\n"
            "core_plugin = midonet.neutron.plugin_v2.MidonetPluginV2\n"
            "service_plugins = lbaas\n"
            "auth_strategy = noauth\n"
            "rpc_backend = neutron.openstack.common.rpc.impl_kombu\n"
            "rabbit_host = localhost\n"
            "rabbit_userid = guest\n"
            "rabbit_password = cat\n"
            "allow_overlapping_ips = True\n"
            "router_scheduler_driver =\n"
            "debug = True\n"
            "\n"
            "[agent]\n"
            "root_helper = sudo /usr/bin/neutron-rootwrap "
            "/etc/neutron/rootwrap.conf\n"
            "\n"
            "[database]\n"
            "connection = mysql://neutron:cat@localhost/neutron\n"
            "\n"
            "[oslo_concurrency]\n"
            "lock_path = $state_path/lock\n")

        cli.copy_file('/etc/neutron/neutron.conf',
                      '/etc/neutron/neutron.conf.bak')
        cli.write_to_file('/etc/neutron/neutron.conf', cfg_file_str)

        dhcp_ini_str = (
            "[DEFAULT]\n"
            "interface_driver = "
            "neutron.agent.linux.interface.MidonetInterfaceDriver\n"
            "dhcp_driver = "
            "midonet.neutron.agent.midonet_driver.DhcpNoOpDriver\n"
            "use_namespaces = True\n"
            "dnsmasq_config_file = /etc/neutron/dnsmasq-neutron.conf\n"
            "enable_isolated_metadata = True\n"
            "\n"
            "[MIDONET]\n"
            "midonet_uri = " + mn_api_url + "\n"
            "username = admin\n"
            "password = cat\n"
            "project_id = admin\n"
            "auth_url = http://localhost:5000/v2.0\n")

        cli.copy_file('/etc/neutron/dhcp_agent.ini',
                      '/etc/neutron/dhcp_agent.ini.bak')
        cli.write_to_file('/etc/neutron/dhcp_agent.ini', dhcp_ini_str)

        lbaas_cfg_str = (
            "[service_providers]\n"
            "service_provider = LOADBALANCER:Midonet:"
            "midonet.neutron.services.loadbalancer.driver."
            "MidonetLoadbalancerDriver:default\n")

        cli.copy_file('/etc/neutron/neutron_lbaas.conf',
                      '/etc/neutron/neutron_lbaas.conf.bak')
        cli.write_to_file('/etc/neutron/neutron_lbaas.conf', lbaas_cfg_str)

        mn_plugin_str = (
            "[DATABASE]\n"
            "sql_connection = mysql+mysqlconnector://"
            "neutron:cat@localhost/neutron\n"
            "sql_max_retries = 100\n"
            "[MIDONET]\n"
            "midonet_uri = " + mn_api_url + "\n"
            "username = admin\n"
            "password = cat\n"
            "project_id = admin\n"
            "auth_url = http://localhost:5000/v2.0\n"
            "provider_router_id =\n")

        cli.mkdir('/etc/neutron/plugins/midonet')
        cli.copy_file(
            '/etc/neutron/plugins/midonet/midonet_plugin.ini',
            '/etc/neutron/plugins/midonet/midonet_plugin.ini.bak')
        cli.write_to_file(
            '/etc/neutron/plugins/midonet/midonet_plugin.ini',
            mn_plugin_str)
        cli.rm('/etc/neutron/plugin.ini')
        cli.cmd(
            'ln -s /etc/neutron/plugins/midonet/midonet_plugin.ini '
            '/etc/neutron/plugin.ini')

    @staticmethod
    def liberty_config(mn_api_url):

        cfg_file_str = (
            "[DEFAULT]\n"
            "core_plugin = neutron.plugins.ml2.plugin.Ml2Plugin\n"
            "service_plugins = midonet.neutron.services.l3."
            "l3_midonet.MidonetL3ServicePlugin,"
            "neutron_lbaas.services.loadbalancer.plugin.LoadBalancerPlugin\n"
            "auth_strategy = noauth\n"
            "rpc_backend = neutron.openstack.common.rpc.impl_kombu\n"
            "rabbit_host = localhost\n"
            "rabbit_userid = guest\n"
            "rabbit_password = cat\n"
            "allow_overlapping_ips = True\n"
            "router_scheduler_driver =\n"
            "debug = True\n"
            "\n"
            "[agent]\n"
            "root_helper = sudo /usr/bin/neutron-rootwrap "
            "/etc/neutron/rootwrap.conf\n"
            "\n"
            "[database]\n"
            "connection = mysql://neutron:cat@localhost/neutron\n"
            "\n"
            "[oslo_concurrency]\n"
            "lock_path = $state_path/lock\n")

        cli.copy_file('/etc/neutron/neutron.conf',
                      '/etc/neutron/neutron.conf.bak')
        cli.write_to_file('/etc/neutron/neutron.conf', cfg_file_str)

        dhcp_ini_str = (
            "[DEFAULT]\n"
            "interface_driver = neutron.agent.linux.interface."
            "MidonetInterfaceDriver\n"
            "dhcp_driver = midonet.neutron.agent.midonet_driver."
            "DhcpNoOpDriver\n"
            "use_namespaces = True\n"
            "dnsmasq_config_file = /etc/neutron/dnsmasq-neutron.conf\n"
            "enable_isolated_metadata = True\n"
            "\n"
            "[MIDONET]\n"
            "midonet_uri = " + mn_api_url + "\n"
            "username = admin\n"
            "password = cat\n"
            "project_id = admin\n"
            "auth_url = http://localhost:5000/v2.0\n")

        cli.copy_file('/etc/neutron/dhcp_agent.ini',
                      '/etc/neutron/dhcp_agent.ini.bak')
        cli.write_to_file('/etc/neutron/dhcp_agent.ini', dhcp_ini_str)

        lbaas_cfg_str = (
            "[service_providers]\n"
            "service_provider = LOADBALANCER:Midonet:"
            "midonet.neutron.services.loadbalancer.driver."
            "MidonetLoadbalancerDriver:default\n")

        cli.copy_file('/etc/neutron/neutron_lbaas.conf',
                      '/etc/neutron/neutron_lbaas.conf.bak')
        cli.write_to_file('/etc/neutron/neutron_lbaas.conf', lbaas_cfg_str)

        mn_plugin_str = (
            "[ML2]\n"
            "tenant_network_types = midonet\n"
            "extension_drivers = port_security\n"
            "type_drivers = midonet,uplink\n"
            "mechanism_drivers = midonet\n"
            "[MIDONET]\n"
            "client = midonet.neutron.client.api.MidonetApiClient\n"
            "project_id = admin\n"
            "password = cat\n"
            "username = admin\n"
            "midonet_uri = " + mn_api_url + "\n")

        cli.copy_file('/etc/neutron/plugin.ini',
                      '/etc/neutron/plugin.ini.bak')
        cli.write_to_file('/etc/neutron/plugin.ini', mn_plugin_str)


try:
    arg_map, extra_args = getopt.getopt(
        sys.argv[1:], 'hdv:a:',
        ['help', 'debug', 'version=', 'api-url='])

    # Defaults
    version = "liberty"
    api_url = 'http://localhost:8181/midonet-api'

    for arg, value in arg_map:
        if arg in ('-h', '--help'):
            usage(None)
            sys.exit(0)
        elif arg in ('-v', '--version'):
            version = value
        elif arg in ('-a', '--api-url'):
            api_url = value
        elif arg in ('-d', '--debug'):
            debug = True
        else:
            raise ArgMismatchException('Invalid argument' + arg)

    nc = NeutronComponentInstaller(ost_version=version)
    nc.install_packages()
    nc.configure_for_midonet(mn_api_url=api_url)

except getopt.GetoptError as e:
    usage(None)
    print("Invalid Command Line: " + e.msg)
    exit(1)
except ExitCleanException:
    exit(1)
except ArgMismatchException as a:
    usage(None)
    print('Argument mismatch: ' + str(a))
    exit(2)
except ObjectNotFoundException as e:
    print('Object not found: ' + str(e))
    exit(2)
except SubprocessFailedException as e:
    print('Subprocess failed to execute: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
except TestException as e:
    print('Unknown exception: ' + str(e))
    traceback.print_tb(sys.exc_traceback)
    exit(2)
