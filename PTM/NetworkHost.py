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

import time

from RootHost import RootHost
from ConfigurationHandler import FileConfigurationHandler
from common.Exceptions import *
from common.IP import IP

class NetworkHost(RootHost):
    def __init__(self, name, ptm):
        super(NetworkHost, self).__init__(name, ptm)
        self.zookeeper_ips = []
        self.url = "http://localhost:8080/midonet-api"
        self.configurator = NetworkFileConfiguration()

    def do_extra_config_from_ptc_def(self, cfg, impl_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        implementation-specific configuration
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        :return:
        """
        if 'zookeeper_ips' in impl_cfg.kwargs:
            for i in impl_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'url' in impl_cfg.kwargs:
            self.ip = impl_cfg.kwargs['url']

    def prepare_config(self):
        self.configurator.configure(self.zookeeper_ips)

    def print_config(self, indent=0):
        super(NetworkHost, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Zookeeper-IPs: ' + ', '.join(str(ip) for ip in self.zookeeper_ips)

    def wait_for_process_start(self):
        # Checking MN-API status
        connected = False
        deadline = time.time() + 10
        while not connected:
            if self.cli.cmd('midonet-cli --midonet-url="' + self.url + '" -A -e "host list"', return_status=True) == 0:
                connected = True
            else:
                if time.time() > deadline:
                    raise SubprocessFailedException('Network host timed out while starting')
                time.sleep(1)

    def control_start(self):
        self.cli.cmd('/etc/init.d/tomcat7 restart')
        self.cli.cmd('/etc/init.d/apache2 restart')

    def control_stop(self):
        self.cli.cmd('/etc/init.d/tomcat7 stop')


class NetworkFileConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(NetworkFileConfiguration, self).__init__()

    def configure(self, zookeeper_ips):

        if len(zookeeper_ips) is not 0:
            ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            ip_str = ''

        if not self.cli.exists('/usr/share/midonet-api/WEB-INF/web.xml.original'):
            self.cli.copy_file('/usr/share/midonet-api/WEB-INF/web.xml',
                               '/usr/share/midonet-api/WEB-INF/web.xml.original')

        self.cli.cmd('perl -0777 -i.old -pe '
                     '"s/(<param-name>zookeeper-zookeeper_hosts<\\/param-name>.*?<param-value>)[^<]*(<\\/param-value>)/'
                     '\\${1}' + ip_str + '\\${2}/s" '
                     '/usr/share/midonet-api/WEB-INF/web.xml')

        if not self.cli.grep_file('/usr/share/midonet-api/WEB-INF/web.xml', 'zookeeper-curator_enabled'):
            self.cli.regex_file('/usr/share/midonet-api/WEB-INF/web.xml',
                                (r's/'
                                 r'    <param-name>zookeeper-zookeeper_hosts<\/param-name>/'  # -->
                                 r'    <param-name>zookeeper-curator_enabled<\/param-name>\n'
                                 r'    <param-value>true<\/param-value>\n'
                                 r'  <\/context-param>\n'
                                 r'  <context-param>\n'
                                 r'    <param-name>zookeeper-zookeeper_hosts<\/param-name>/'))

        self.cli.regex_file('/usr/share/midonet-api/WEB-INF/web.xml',
                            ('s/org.midonet.api.auth.keystone.v2_0.KeystoneService/org.midonet.api.auth.MockAuthService/g'))

        tcatcfg = ('<Context path="/midonet-api" docBase="/usr/share/midonet-api"\n'
                   '         antiResourceLocking="false" privileged="true" />')
        self.cli.write_to_file('/etc/tomcat7/Catalina/localhost/midonet-api.xml', tcatcfg)

        if not self.cli.grep_file("/etc/default/tomcat7", "java.security.egd"):
            self.cli.regex_file('/etc/default/tomcat7',
                                '$aJAVA_OPTS="$JAVA_OPTS -Djava.security.egd=file:/dev/./urandom"')

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

