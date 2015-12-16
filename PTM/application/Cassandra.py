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

from PTM.application.Application import Application
from common.Exceptions import *
from common.FileLocation import *
from PTM.PhysicalTopologyConfig import *
from common.CLI import *
from common.IP import IP
from ConfigurationHandler import FileConfigurationHandler


class Cassandra(Application):
    @staticmethod
    def get_name():
        return 'cassandra'

    def __init__(self, host, app_id=''):
        super(Cassandra, self).__init__(host, app_id)
        self.cassandra_ips = []
        self.num_id = '1'
        self.init_token = ''
        self.ip = IP()
        self.configurator = CassandraFileConfiguration()

    def configure(self, host_cfg, app_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        app-specific configuration
        :type host_cfg: HostDef
        :type app_cfg: ApplicationDef
        :return:
        """
        if len(host_cfg.interfaces.values()) > 0 and len(host_cfg.interfaces.values()[0].ip_addresses) > 0:
            self.ip = host_cfg.interfaces.values()[0].ip_addresses[0]

        if 'init_token' in app_cfg.kwargs:
            self.init_token = app_cfg.kwargs['init_token']

        if 'cassandra_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['cassandra_ips']:
                self.cassandra_ips.append(IP(i))

        if 'id' in app_cfg.kwargs:
            self.num_id = app_cfg.kwargs['id']

    def prepare_config(self, log_manager):
        self.configurator.configure(self.num_id, self.cassandra_ips, self.init_token, self.ip)
        log_dir = '/var/log/cassandra.' + self.num_id
        log_manager.add_external_log_file(FileLocation(log_dir + '/system.log'), self.num_id,
                                               '%Y-%m-%d %H:%M:%S,%f', 2)

    def print_config(self, indent=0):
        super(Cassandra, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Num-id: ' + self.num_id
        print ('    ' * (indent + 1)) + 'Init-token: ' + self.init_token
        print ('    ' * (indent + 1)) + 'Self-IP: ' + str(self.ip)
        print ('    ' * (indent + 1)) + 'Cassandra-IPs: ' + ', '.join(str(ip) for ip in self.cassandra_ips)

    def create_cfg_map(self):
        return {'num_id': self.num_id, 'ip': self.ip.to_map()}

    def config_app_for_process_control(self, cfg_map):
        self.num_id = cfg_map['num_id']
        self.ip = IP.from_map(cfg_map['ip'])

    def wait_for_process_start(self):
        # Wait a couple seconds for the process to start before polling nodetool
        time.sleep(2)
        # Checking Cassandra status
        retries = 0
        max_retries = 10
        connected = False
        while not connected:
            if self.cli.cmd('nodetool -h 127.0.0.1 status').ret_code == 0:
                connected = True
            else:
                retries += 1
                if retries > max_retries:
                    raise SocketException('Cassandra host ' + self.num_id + ' timed out while starting')
                time.sleep(2)

    def prepare_environment(self):
        self.configurator.mount_config(self.num_id)

    def cleanup_environment(self):
        self.configurator.unmount_config()

    def control_start(self):
        self.cli.cmd('/bin/bash -c "MAX_HEAP_SIZE=128M HEAP_NEWSIZE=64M /etc/init.d/cassandra start"')

    def control_stop(self):
        self.cli.cmd("/etc/init.d/cassandra stop")


class CassandraFileConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(CassandraFileConfiguration, self).__init__()

    def configure(self, num_id, cassandra_ips, init_token, self_ip):
        seed_str = ''.join([ip.ip + ',' for ip in cassandra_ips])[:-1]

        etc_dir = '/etc/cassandra.' + num_id
        var_lib_dir = '/var/lib/cassandra.' + num_id
        var_log_dir = '/var/log/cassandra.' + num_id
        var_run_dir = '/run/cassandra.' + num_id

        self.cli.rm(etc_dir)
        self.cli.copy_dir('/etc/cassandra', etc_dir)

        # Work around for https://issues.apache.org/jira/browse/CASSANDRA-5895
        self.cli.regex_file(etc_dir + '/cassandra-env.sh', 's/-Xss[1-9][0-9]*k/-Xss228k/')

        self.cli.replace_text_in_file(etc_dir + '/cassandra-env.sh',
                                      '# JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname=<public name>"',
                                      'JVM_OPTS="$JVM_OPTS -Djava.rmi.server.hostname=' + self_ip.ip + '"')

        self.cli.regex_file_multi(etc_dir + '/cassandra.yaml',
                                  "s/^cluster_name:.*$/cluster_name: 'midonet'/",
                                  's/^initial_token:.*$/initial_token: ' + init_token + '/',
                                  "/^seed_provider:/,/^$/ s/seeds:.*$/seeds: '" + seed_str + "'/",
                                  's/^listen_address:.*$/listen_address: ' + self_ip.ip + '/',
                                  's/^rpc_address:.*$/rpc_address: ' + self_ip.ip + '/')

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir)
        self.cli.chown(var_lib_dir, 'cassandra', 'cassandra')

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)
        self.cli.chown(var_log_dir, 'cassandra', 'cassandra')

        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)
        self.cli.chown(var_run_dir, 'cassandra', 'cassandra')

    def mount_config(self, num_id):
        self.cli.mount('/run/cassandra.' + num_id, '/run/cassandra')
        self.cli.mount('/var/lib/cassandra.' + num_id, '/var/lib/cassandra')
        self.cli.mount('/var/log/cassandra.' + num_id, '/var/log/cassandra')
        self.cli.mount('/etc/cassandra.' + num_id, '/etc/cassandra')

    def unmount_config(self):
        self.cli.unmount('/run/cassandra')
        self.cli.unmount('/var/lib/cassandra')
        self.cli.unmount('/var/log/cassandra')
        self.cli.unmount('/etc/cassandra')

