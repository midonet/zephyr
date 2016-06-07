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

import time
import uuid

from zephyr.cbt import version_config
from zephyr.common.exceptions import *
from zephyr.common.file_location import *
from zephyr.common.ip import IP
from zephyr.ptm.application.application import Application
from zephyr.ptm.application.configuration_handler import (
    FileConfigurationHandler)
from zephyr.ptm.ptm_constants import APPLICATION_START_TIMEOUT


# TODO(micucci): This is really the controller and should be refactored in
# case it's not on root or same host as a Compute
class MidonetAPI(Application):

    @staticmethod
    def get_name():
        return 'midonet-api'

    def __init__(self, host, app_id=''):
        super(MidonetAPI, self).__init__(host, app_id)
        self.zookeeper_ips = []
        self.cassandra_ips = []
        self.unique_id = uuid.uuid4()
        self.use_cluster = version_config.ConfigMap.get_configured_parameter(
            'option_api_uses_cluster')
        self.configurator = (ClusterConfiguration()
                             if self.use_cluster
                             else TomcatFileConfiguration())
        self.url = version_config.ConfigMap.get_configured_parameter(
            'param_midonet_api_url')
        self.ip = None

    def configure(self, host_cfg, app_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        app-specific configuration
        :type host_cfg: HostDef
        :type app_cfg: ApplicationDef
        :return:
        """
        if 'cassandra_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['cassandra_ips']:
                self.cassandra_ips.append(IP(i))

        if 'zookeeper_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'url' in app_cfg.kwargs:
            self.ip = app_cfg.kwargs['url']

    def prepare_config(self, log_manager):
        self.configurator.configure(self.zookeeper_ips, self.unique_id)

        if self.use_cluster:
            log_dir = '/var/log/midonet-cluster'
            log_manager.add_external_log_file(
                FileLocation(log_dir + '/midonet-cluster.log'), '',
                '%b %d, %Y %I:%M:%S %p')
            LinuxCLI().replace_text_in_file(
                '/etc/midonet-cluster/logback.xml',
                'root level="INFO"', 'root level="DEBUG"')
        else:
            LinuxCLI().replace_text_in_file(
                '/usr/share/midonet-api/WEB-INF/classes/logback.xml',
                'root level="INFO"', 'root level="DEBUG"')
            log_dir = '/var/log/tomcat7'
            log_manager.add_external_log_file(
                FileLocation(log_dir + '/catalina.out'), '',
                '%b %d, %Y %I:%M:%S %p')
            log_manager.add_external_log_file(
                FileLocation(log_dir + '/midonet-api.log'), '',
                '%Y.%m.%d %H:%M:%S.%f')

    def print_config(self, indent=0):
        super(MidonetAPI, self).print_config(indent)
        print(('    ' * (indent + 1)) + 'Zookeeper-IPs: ' +
              ', '.join(str(ip) for ip in self.zookeeper_ips))
        print(('    ' * (indent + 1)) + 'Cassandra-IPs: ' +
              ', '.join(str(ip) for ip in self.cassandra_ips))

    def wait_for_process_start(self):
        # Checking MN-API status
        connected = False
        deadline = time.time() + APPLICATION_START_TIMEOUT + 2000
        self.LOG.debug("Waiting for API to start on URL: " + self.url)
        while not connected:
            if self.use_cluster:
                if self.cli.grep_cmd(
                        'tac /var/log/midonet-cluster/midonet-cluster.log',
                        "MidoNet Cluster \(started\|is up\)",
                        options='-m1'):
                    connected = True
                else:
                    if time.time() > deadline:
                        raise SubprocessFailedException(
                            'Cluster timed out while starting')
            else:
                if self.cli.cmd('midonet-cli --midonet-url="' + self.url +
                                '" -A -e "host list"').ret_code == 0:
                    connected = True
                else:
                    if time.time() > deadline:
                        raise SubprocessFailedException(
                            'Network host timed out while starting')
                    time.sleep(1)

    def control_start(self):
        if self.use_cluster:
            LinuxCLI(log_cmd=True).cmd('/etc/init.d/midonet-cluster restart')
        else:
            LinuxCLI(log_cmd=True).cmd('/etc/init.d/tomcat7 restart')
            LinuxCLI(log_cmd=True).cmd('/etc/init.d/apache2 restart')

    def control_stop(self):
        if self.use_cluster:
            LinuxCLI(log_cmd=True).cmd('/etc/init.d/midonet-cluster stop')
        else:
            LinuxCLI(log_cmd=True).cmd('/etc/init.d/tomcat7 stop')


# noinspection PyUnresolvedReferences
class TomcatFileConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(TomcatFileConfiguration, self).__init__()

    def configure(self, zookeeper_ips, unique_id=0):

        if len(zookeeper_ips) is not 0:
            ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            ip_str = ''

        if not self.cli.exists(
                '/usr/share/midonet-api/WEB-INF/web.xml.original'):
            self.cli.copy_file(
                '/usr/share/midonet-api/WEB-INF/web.xml',
                '/usr/share/midonet-api/WEB-INF/web.xml.original')

        self.cli.cmd(
            'perl -0777 -i.old -pe '
            '"s/(<param-name>zookeeper-zookeeper_hosts<\\/param-name>.*?'
            '<param-value>)[^<]*(<\\/param-value>)/'
            '\\${1}' + ip_str + '\\${2}/s" '
            '/usr/share/midonet-api/WEB-INF/web.xml')

        if not self.cli.grep_file(
                '/usr/share/midonet-api/WEB-INF/web.xml',
                'zookeeper-curator_enabled'):
            self.cli.regex_file(
                '/usr/share/midonet-api/WEB-INF/web.xml',
                (r's/'
                 r'    <param-name>zookeeper-zookeeper_hosts<\/param-name>/'
                 r'    <param-name>zookeeper-curator_enabled<\/param-name>\n'
                 r'    <param-value>true<\/param-value>\n'
                 r'  <\/context-param>\n'
                 r'  <context-param>\n'
                 r'    <param-name>zookeeper-zookeeper_hosts<\/param-name>/'))

        self.cli.regex_file(
            '/usr/share/midonet-api/WEB-INF/web.xml',
            ('s/org.midonet.api.auth.keystone.v2_0.KeystoneService/'
             'org.midonet.cluster.auth.MockAuthService/g'))

        tcatcfg = (
            '<Context path="/midonet-api" docBase="/usr/share/midonet-api"\n'
            '         antiResourceLocking="false" privileged="true" />')
        self.cli.write_to_file(
            '/etc/tomcat7/Catalina/localhost/midonet-api.xml', tcatcfg)

        if not self.cli.grep_file("/etc/default/tomcat7", "java.security.egd"):
            self.cli.regex_file(
                '/etc/default/tomcat7',
                '$aJAVA_OPTS="$JAVA_OPTS -Djava.security.egd='
                'file:/dev/./urandom"')

        if self.cli.exists('/var/www/html/midonet-cp/config.js'):
            self.cli.regex_file('/var/www/html/midonet-cp/config.js',
                                ('s%https://example.com/midonet-api%'
                                 'http://$public:8080/midonet-api%g;'
                                 's/example.com/'
                                 '$public:8443/g'))
        elif self.cli.exists('/var/www/midonet-cp/config.js'):
            self.cli.regex_file('/var/www/midonet-cp/config.js',
                                ('s%https://example.com/midonet-api%'
                                 'http://$public:8080/midonet-api%g;'
                                 's/example.com/'
                                 '$public:8443/g'))

        self.cli.rm('/etc/midonet_host_id.properties')
        uuid_str = 'host_uuid=' + str(unique_id) + '\n'
        self.cli.write_to_file('/etc/midolman/host_uuid.properties', uuid_str)

        conf_str = ("[zookeeper]\n"
                    "zookeeper_hosts = " + ip_str + "\n")
        self.cli.write_to_file('/etc/midonet/midonet.conf', conf_str)


class ClusterConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(ClusterConfiguration, self).__init__()

    def configure(self, zookeeper_ips, unique_id):
        if len(zookeeper_ips) is not 0:
            z_ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            z_ip_str = ''

        zkcli = LinuxCLI()
        zkcli.add_environment_variable('MIDO_ZOOKEEPER_HOSTS', z_ip_str)

        self.cli.rm('/var/log/midonet-cluster/midonet-cluster.log')
        self.cli.rm('/etc/midonet_host_id.properties')
        uuid_str = 'host_uuid=' + str(unique_id) + '\n'
        self.cli.write_to_file('/etc/midolman/host_uuid.properties', uuid_str)

        conf_str = "[zookeeper]\n" \
                   "zookeeper_hosts = " + z_ip_str + "\n"
        self.cli.write_to_file('/etc/midonet/midonet.conf', conf_str)
        zkcli.cmd('mn-conf set -t default "agent.cluster.enabled: true"')
