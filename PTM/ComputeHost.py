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

from Host import Host
from VMHost import VMHost
from common.CLI import NetNSCLI, CREATENSCMD, REMOVENSCMD
from common.Exceptions import *
from PhysicalTopologyConfig import IPDef


class ComputeHost(Host):
    global_id = 1

    def __init__(self, name, cli, host_create_func, host_remove_func, root_host):
        super(ComputeHost, self).__init__(name, cli, host_create_func, host_remove_func, root_host)
        self.vms = {}
        self.num_id = str(len(root_host.compute_hosts) + 1)
        self.zookeeper_ips = []
        self.cassandra_ips = []

    def print_config(self, indent=0):
        super(ComputeHost, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Num-id: ' + self.num_id
        print ('    ' * (indent + 1)) + 'Zookeeper-IPs: ' + ', '.join(str(ip) for ip in self.zookeeper_ips)
        print ('    ' * (indent + 1)) + 'Cassandra-IPs: ' + ', '.join(str(ip) for ip in self.cassandra_ips)
        if len(self.vms) > 0:
            print ('    ' * (indent + 1)) + 'Hosted vms: '
            for vm in self.vms:
                vm.print_config(indent + 2)
                print ('    ' * (indent + 4)) + 'Interfaces:'
                for name,i in self.get_interfaces_for_host(vm.get_name()).items():
                    print ('    ' * (indent + 5)) + name
                    i.print_config(indent + 6)

    def prepare_files(self):
        etc_dir = '/etc/midolman.' + self.num_id
        var_lib_dir = '/var/lib/midolman.' + self.num_id
        var_log_dir = '/var/lib/midolman.' + self.num_id
        var_run_dir = '/run/midolman.' + self.num_id

        self.cli.rm(etc_dir)
        self.cli.copy_dir('/etc/midolman', etc_dir)

        # generates host uuid
        host_uuid = ('# generated for MMM MM $n\n'
                     'host_uuid=00000000-0000-0000-0000-00000000000') + self.num_id
        self.cli.write_to_file(etc_dir + '/host_uuid.properties', host_uuid, False)

        mmconf = etc_dir + '/midolman.conf'

        if len(self.zookeeper_ips) is not 0:
            z_ip_str = ''.join([str(ip.ip_address) + ':2181,' for ip in self.zookeeper_ips])[:-1]
        else:
            z_ip_str = ''

        if len(self.cassandra_ips) is not 0:
            c_ip_str = ''.join([str(ip.ip_address) + ',' for ip in self.cassandra_ips])[:-1]
        else:
            c_ip_str = ''

        self.cli.regex_file(mmconf,
                            '/^\[zookeeper\]/,/^$/ s/^zookeeper_hosts =.*$/zookeeper_hosts = ' +
                            z_ip_str + '/')

        self.cli.regex_file(mmconf,
                            '/^\[cassandra\]/,/^$/ s/^servers =.*$/servers = ' +
                            c_ip_str + '/;s/^replication_factor =.*$/replication_factor = 3/')

        self.cli.regex_file(mmconf,
                            ('/^\[midolman\]/,/^\[/ s%^[# ]*bgpd_binary = /usr/lib/quagga.*$%bg'
                             'pd_binary = /usr/lib/quagga%'))

        if not self.cli.grep_file(mmconf, '\[haproxy_health_monitor\]'):
            hmoncfg = ('# Enable haproxy on the node.\n'
                       '[haproxy_health_monitor]\n'
                       'namespace_cleanup = true\n'
                       'health_monitor_enable = true\n'
                       'haproxy_file_loc =') + etc_dir + '/l4lb/\n'
            self.cli.write_to_file(mmconf, hmoncfg, True)

        lb = etc_dir + '/logback.xml'

        self.cli.regex_file(lb, 's/root level="INFO"/root level="DEBUG"/')
        self.cli.regex_file(lb, '/<rollingPolicy/, /<\/rollingPolicy/d')
        self.cli.regex_file(lb, 's/rolling.RollingFileAppender/FileAppender/g')

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir)

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)

        self.cli.mkdir('/run/midolman')
        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)

        mmenv = etc_dir + '/midolman-env.sh'

        # Allow connecting via debugger - MM 1 listens on 1411, MM 2 on 1412, MM 3 on 1413
        self.cli.regex_file(mmenv, '/runjdwp/s/^..//g')
        self.cli.regex_file(mmenv, '/runjdwp/s/1414/141' + self.num_id + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/65ace0e84265cd777b2855d15fce60148abd9330
        self.cli.regex_file(mmenv, 's/MAX_HEAP_SIZE=.*/MAX_HEAP_SIZE="300M"/')
        self.cli.regex_file(mmenv, 's/HEAP_NEWSIZE=.*/HEAP_NEWSIZE="200M"/')

    def start_process(self):
        if self.num_id == '1':
            pid_file = '/run/midolman.' + self.num_id + '/dnsmasq.pid'

            pid = self.cli.cmd('dnsmasq --no-host --no-resolv -S 8.8.8.8 & echo $! &', return_output=True)
            self.cli.rm(pid_file)
            self.cli.write_to_file(pid_file, pid)

        self.cli.cmd_unshare_control('control compute ' + self.num_id + ' start')

    def stop_process(self):
        self.cli.cmd_unshare_control('control compute ' + self.num_id + ' stop')

        if self.num_id == '1':
            pid_file = '/run/midolman.' + self.num_id + '/dnsmasq.pid'

            if self.cli.exists(pid_file):
                pid = self.cli.read_from_file(pid_file)
                self.cli.cmd('kill ' + str(pid))
                self.cli.rm(pid_file)

    def mount_shares(self):
        self.cli.mount('/run/midolman.' + self.num_id, '/run/midolman')
        self.cli.mount('/var/lib/midolman.' + self.num_id, '/var/lib/midolman')
        self.cli.mount('/var/log/midolman.' + self.num_id, '/var/log/midolman')
        self.cli.mount('/etc/midolman.' + self.num_id, '/etc/midolman')

    def unmount_shares(self):
        self.cli.unmount('/run/midolman.' + self.num_id)
        self.cli.unmount('/var/lib/midolman')
        self.cli.unmount('/var/log/midolman')
        self.cli.unmount('/etc/midolman')

    def control_start(self, *args):
        self.cli.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        pid = self.cli.cmd('/usr/share/midolman/midolman-start & echo $! &', return_output=True)
        if pid == -1:
            raise SubprocessFailedException('midolman')
        self.cli.write_to_file('/run/midolman/pid', pid)

    def control_stop(self, *args):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))

    def create_vm(self, name):
        new_host = VMHost(name, NetNSCLI(name), CREATENSCMD, REMOVENSCMD, self)
        self.vms[name] = new_host
        return new_host

    def get_vm(self, name):
        if name not in self.vms:
            raise HostNotFoundException(name)
        return self.vms[name]

    def setup_vms(self):
        for name, vm in self.vms.iteritems():
            print 'Booting vm ' + name
            vm.add()
            self.add_host_interfaces(vm)

    def cleanup_vms(self):
        for name, vm in self.vms.iteritems():
            self.delete_host_interfaces(vm)
            vm.unlink_interfaces()

    def start_vms(self):
        for name, vm in self.vms.iteritems():
            print 'Starting vm ' + name
            vm.start_process()

    def stop_vms(self):
        for name, vm in self.vms.iteritems():
            vm.stop_process()

    def connect_iface_to_port(self, vm_name, iface, port_id):
        if vm_name not in self.interfaces_for_host:
            raise HostNotFoundException(vm_name)
        if iface not in self.interfaces_for_host[vm_host]:
            raise ObjectNotFoundException('interface ' + iface + ' not on host ' + vm_name)
        return self.cli.cmd('mm-ctl --bind-port ' +
                            port_id + ' ' +
                            self.interfaces_for_host[vm_host][iface].name)

    def disconnect_port(self, port_id):
        return self.cli.cmd('mm-ctl --unbind-port ' + port_id)
