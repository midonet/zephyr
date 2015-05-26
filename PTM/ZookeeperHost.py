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

import time
import socket

from common.Exceptions import *
from Host import Host
from PhysicalTopologyConfig import HostDef, IPDef

class ZookeeperHost(Host):
    global_id = 1

    def __init__(self, name, cli, host_create_func, host_remove_func, root_host):
        super(ZookeeperHost, self).__init__(name, cli,
                                            host_create_func,
                                            host_remove_func,
                                            root_host)
        self.zookeeper_ips = []
        self.num_id = str(len(root_host.zookeeper_hosts) + 1)
        self.ip = IPDef('', '')
        self.pid = 0

    def print_config(self, indent=0):
        super(ZookeeperHost, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Num-id: ' + self.num_id
        print ('    ' * (indent + 1)) + 'Self-IP: ' + str(self.ip)
        print ('    ' * (indent + 1)) + 'Zookeeper-IPs: ' + ', '.join(str(ip) for ip in self.zookeeper_ips)


    def prepare_files(self):
        if self.num_id == '1':
            etc_dir = '/etc/zookeeper.test'
            self.cli.rm(etc_dir)
            self.cli.copy_dir('/etc/zookeeper', etc_dir)

            write_string = ''
            for j in range(0, len(self.zookeeper_ips)):
                write_string += 'server.' + str(j + 1) + '=' + str(self.zookeeper_ips[j].ip_address) + ':2888:3888\n'

            print 'write_str=' + write_string
            self.cli.write_to_file(etc_dir + '/conf/zoo.cfg', write_string, append=True)

        var_lib_dir = '/var/lib/zookeeper.' + self.num_id
        var_log_dir = '/var/log/zookeeper.' + self.num_id
        var_run_dir = '/run/zookeeper.' + self.num_id

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir + '/data')
        self.cli.write_to_file(var_lib_dir + '/data/myid', self.num_id, False)
        self.cli.write_to_file(var_lib_dir + '/myid', self.num_id, False)
        self.cli.chown(var_lib_dir, 'zookeeper', 'zookeeper')

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)
        self.cli.chown(var_log_dir, 'zookeeper', 'zookeeper')

        self.cli.mkdir('/run/zookeeper')
        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)
        self.cli.chown(var_run_dir, 'zookeeper', 'zookeeper')

    def start(self):
        self.cli.cmd_unshare_control('control zookeeper ' + self.num_id + ' start')

        # Checking Zookeeper status
        retries = 0
        max_retries = 10
        connected = False
        while not connected:
            ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                ping_socket.connect((self.ip.ip_address, 2181))
                ping_socket.send('ruok')
                if ping_socket.recv(16) == 'imok':
                    connected = True
                else:
                    retries += 1
                    if retries > max_retries:
                        raise SocketException('Zookeeper host ' + self.num_id + ' timed out while starting')
                    time.sleep(2)
            except SocketException:
                raise
            except Exception:
                pass

    def stop(self):
        self.cli.cmd_unshare_control('control zookeeper ' + self.num_id + ' stop')

    def mount_shares(self):
        self.cli.mount('/run/zookeeper.' + self.num_id, '/run/zookeeper')
        self.cli.mount('/var/lib/zookeeper.' + self.num_id, '/var/lib/zookeeper')
        self.cli.mount('/var/log/zookeeper.' + self.num_id, '/var/log/zookeeper')
        self.cli.mount('/etc/zookeeper.test', '/etc/zookeeper')

    def unmount_shares(self):
        self.cli.unmount('/run/zookeeper')
        self.cli.unmount('/var/lib/zookeeper')
        self.cli.unmount('/var/log/zookeeper')
        self.cli.unmount('/etc/zookeeper')

    def control_start(self, *args):
        self.cli.rm_files('/var/log/zookeeper')
        pid = self.cli.cmd(('/usr/bin/java'
                            ' -cp /etc/zookeeper/conf:'
                                 '/usr/share/java/jline.jar:'
                                 '/usr/share/java/log4j-1.2.jar:'
                                 '/usr/share/java/xercesImpl.jar:'
                                 '/usr/share/java/xmlParserAPIs.jar:'
                                 '/usr/share/java/netty.jar:'
                                 '/usr/share/java/slf4j-api.jar:'
                                 '/usr/share/java/slf4j-log4j12.jar:'
                                 '/usr/share/java/zookeeper.jar'
                            ' -Dcom.sun.management.jmxremote'
                            ' -Dcom.sun.management.jmxremote.local.only=false'
                            ' -Dzookeeper.log.dir=/var/log/zookeeper'
                            ' -Dzookeeper.root.logger=INFO,ROLLINGFILE'
                            ' org.apache.zookeeper.server.quorum.QuorumPeerMain'
                            ' /etc/zookeeper/conf/zoo.cfg & echo $! &'),
                           return_output=True)
        if pid == -1:
            raise SubprocessFailedException('java-zookeeper')
        self.cli.write_to_file('/run/zookeeper/pid', pid)

    def control_stop(self, *args):
        if self.cli.exists('/run/zookeeper/pid'):
            pid = self.cli.read_from_file('/run/zookeeper/pid')
            self.cli.cmd('kill ' + str(pid))
