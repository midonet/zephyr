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

from common.Exceptions import *
from common.CLI import LinuxCLI
from CBT.installers.ComponentInstaller import ComponentInstaller
from CBT.repos.PackageRepo import PackageRepo
import CBT.VersionConfig as version_config

class NeutronComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo_obj, scheme, repo, username=None, password=None,
                         version=None, distribution='stable'):
        """
        :type repo: PackageRepo
        """
        LinuxCLI().cmd("add-apt-repository -y cloud-archive:" + str(version))
        LinuxCLI().cmd("apt-get update")

    def install_packages(self, repo, exact_version=None):
        if repo.get_type() == "rpm":
            raise ArgMismatchException("Not yet supported on Redhat!")
            #neutron_dep_packages = ['mysql', 'rabbitmq-server']
            #neutron_packages = ['openstack-neutron', 'python-neutronclient', 'openstack-neutron-ml2']

        cli = LinuxCLI(log_cmd=True)

        cli.cmd("sudo debconf-set-selections <<< 'mysql-server-5.1 mysql-server/root_password password 'cat''")
        cli.cmd("sudo debconf-set-selections <<< 'mysql-server-5.1 mysql-server/root_password_again password 'cat''")

        if not repo.is_installed('mysql-server-5.5'):
            repo.install_packages(['mysql-server-5.5', 'mysql-client-5.5', 'python-mysqldb'])

        cli.cmd('mysqladmin -u root password cat')
        cli.regex_file('/etc/mysql/my.cnf', 's/.*bind-address.*/bind-address = 127.0.0.1/')
        cli.regex_file('/etc/mysql/my.cnf', 's/.*max_connections.*/max_connections = 1024/')
        cli.cmd("service mysql start")

        if not repo.is_installed('rabbitmq-server'):
            repo.install_packages(['rabbitmq-server'])

        cli.cmd("rabbitmqctl change_password guest cat")
        cli.cmd("service rabbitmq-server restart")

        if not repo.is_installed('neutron-server'):
            repo.install_packages(['neutron-server', 'neutron-dhcp-agent', 'python-neutronclient',
                                   'python-neutron-lbaas', 'python-mysql.connector'])

            cli.cmd('mysql --user=root --password=cat -e "CREATE DATABASE IF NOT EXISTS neutron"')
            cli.cmd('mysql --user=root --password=cat -e "CREATE USER neutron@localhost IDENTIFIED BY \'cat\'"')
            cli.cmd('mysql --user=root --password=cat -e "CREATE USER neutron@\'%\' IDENTIFIED BY \'cat\'"')
            cli.cmd('mysql --user=root --password=cat -e "GRANT ALL PRIVILEGES ON neutron.* TO neutron@localhost"')
            cli.cmd('mysql --user=root --password=cat -e "GRANT ALL PRIVILEGES ON neutron.* TO neutron@\'%\'"')

        version_config.get_installed_midolman_version()
        mn_api_url = version_config.ConfigMap.get_configured_parameter('param_midonet_api_url')

        cfg_file_str = ("[DEFAULT]\n"
                        "core_plugin = midonet.neutron.plugin_v2.MidonetPluginV2\n"
                        "auth_strategy = noauth\n"
                        "rpc_backend = neutron.openstack.common.rpc.impl_kombu\n"
                        "rabbit_host = localhost\n"
                        "rabbit_userid = guest\n"
                        "rabbit_password = cat\n"
                        "service_plugins = lbaas\n"
                        "allow_overlapping_ips = True\n"
                        "router_scheduler_driver =\n"
                        "\n"
                        "[agent]\n"
                        "root_helper = sudo /usr/bin/neutron-rootwrap /etc/neutron/rootwrap.conf\n"
                        "\n"
                        "[database]\n"
                        "connection = mysql://neutron:cat@localhost/neutron\n"
                        "\n"
                        "[oslo_concurrency]\n"
                        "lock_path = $state_path/lock\n")

        cli.write_to_file('/etc/neutron/neutron.conf', cfg_file_str)

        dhcp_ini_str = ("[DEFAULT]\n"
                        "interface_driver = neutron.agent.linux.interface.MidonetInterfaceDriver\n"
                        "dhcp_driver = midonet.neutron.agent.midonet_driver.DhcpNoOpDriver\n"
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

        cli.write_to_file('/etc/neutron/dhcp_agent.ini', dhcp_ini_str)

        lbaas_cfg_str = ("[service_providers]\n"
                         "service_provider = LOADBALANCER:Midonet:"
                            "midonet.neutron.services.loadbalancer.driver.MidonetLoadbalancerDriver:default\n")

        cli.write_to_file('/etc/neutron/neutron_lbaas.conf', lbaas_cfg_str)

        mn_plugin_str = ("[DATABASE]\n"
                         "sql_connection = mysql+mysqlconnector://neutron:cat@localhost/neutron\n"
                         "sql_max_retries = 100\n"
                         "[MIDONET]\n"
                         "midonet_uri = " + mn_api_url + "\n"
                         "username = admin\n"
                         "password = cat\n"
                         "project_id = admin\n"
                         "auth_url = http://localhost:5000/v2.0\n"
                         "provider_router_id =\n")

        cli.mkdir('/etc/neutron/plugins/midonet')
        cli.write_to_file('/etc/neutron/plugins/midonet/midonet_plugin.ini', mn_plugin_str)
        cli.rm('/etc/neutron/plugin.ini')
        cli.cmd('ln -s /etc/neutron/plugins/midonet/midonet_plugin.ini /etc/neutron/plugin.ini')

        if exact_version == "kilo" or exact_version is None:
            cli.cmd('neutron-db-manage --config-file /etc/neutron/neutron.conf '
                    '--config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head')
            cli.cmd('midonet-db-manage upgrade head')
        else:
            cli.cmd('neutron-db-manage --config-file /etc/neutron/neutron.conf '
                    '--config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade ' + exact_version)
            cli.cmd('midonet-db-manage upgrade ' + exact_version)

        cli.write_to_file('/etc/default/neutron-server', 'NEUTRON_PLUGIN_CONFIG="/etc/neutron/plugin.ini"\n')

        cli.cmd("service neutron-server restart")
        cli.cmd("service neutron-dhcp-agent restart")

        repo.install_packages(['neutron-server', 'neutron-dhcp-agent', 'python-neutronclient',
                               'python-neutron-lbaas', 'python-mysql.connector'])

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        pass

    def is_installed(self, repo):
        return repo.is_installed(['neutron-server'])

