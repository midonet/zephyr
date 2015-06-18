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
import uuid

from common.Exceptions import *
from common.IP import IP

from ConfigurationHandler import FileConfigurationHandler
from NetNSHost import NetNSHost
from VMHost import VMHost
from PhysicalTopologyConfig import InterfaceDef
from Interface import Interface
from VirtualInterface import VirtualInterface


class ComputeHost(NetNSHost):
    """
    Implements the HypervisorHost contract to create VMs
    """
    def __init__(self, name, ptm):
        super(ComputeHost, self).__init__(name, ptm)
        self.vms = {}
        """ :type: dict [str, dict [str, Interface]]"""
        self.num_id = '1'
        self.unique_id = uuid.uuid4()
        self.zookeeper_ips = []
        self.cassandra_ips = []
        self.configurator = ComputeFileConfiguration()

    def do_extra_config_from_ptc_def(self, cfg, impl_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        implementation-specific configuration
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        :return:
        """
        if 'cassandra_ips' in impl_cfg.kwargs:
            for i in impl_cfg.kwargs['cassandra_ips']:
                self.cassandra_ips.append(IP(i))

        if 'zookeeper_ips' in impl_cfg.kwargs:
            for i in impl_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'id' in impl_cfg.kwargs:
            self.num_id = impl_cfg.kwargs['id']

    def print_config(self, indent=0):
        super(ComputeHost, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Num-id: ' + self.num_id
        print ('    ' * (indent + 1)) + 'Zookeeper-IPs: ' + ', '.join(str(ip) for ip in self.zookeeper_ips)
        print ('    ' * (indent + 1)) + 'Cassandra-IPs: ' + ', '.join(str(ip) for ip in self.cassandra_ips)
        if len(self.vms) > 0:
            print ('    ' * (indent + 1)) + 'Hosted vms: '
            for vm in self.vms:
                vm.print_config(indent + 2)

    def prepare_config(self):
        self.configurator.prepare_files(self.num_id, self.unique_id, self.zookeeper_ips, self.cassandra_ips)

    def do_extra_create_host_cfg_map_for_process_control(self):
        return {'num_id': self.num_id, 'uuid': str(self.unique_id)}

    def do_extra_config_host_for_process_control(self, cfg_map):
        self.num_id = cfg_map['num_id']
        self.unique_id = uuid.UUID('urn:uuid:' + cfg_map['uuid'])

    def wait_for_process_start(self):
        retries = 0
        max_retries = 30
        connected = False
        while not connected:
            if self.cli.grep_cmd('mm-dpctl --list-dps', 'midonet') is True:
                connected = True
            else:
                retries += 1
                if retries > max_retries:
                    raise SubprocessFailedException('MidoNet Agent host ' + self.num_id + ' timed out while starting')
                time.sleep(1)

    def prepare_environment(self):
        self.configurator.mount_config(self.num_id)

    def cleanup_environment(self):
        self.configurator.unmount_config(self.num_id)

    def is_hypervisor(self):
        return True

    def create_vm(self, name):
        """
        Create a VM and return it
        :type name: str
        :return: VMHost
        """
        new_host = VMHost(name, self.ptm, self)
        new_host.create()
        new_host.boot()
        new_host.net_up()
        new_host.net_finalize()
        self.vms[name] = new_host
        return new_host
    
    def get_vm(self, name):
        if name not in self.vms:
            raise HostNotFoundException(name)
        return self.vms[name]

    def get_vm_count(self):
        return len(self.vms)

    def create_interface_for_vm(self, vm_host, iface):
        """
        Add an interface to the given VM with the given parameters
        :type vm_host: VMHost
        :type iface: Interface
        """
        near_if_name = vm_host.name + iface.name
        self.link_interface(Interface(near_if_name, self), vm_host, iface)
        near_if = self.interfaces[near_if_name]
        """ :type: VirtualInterface"""
        near_if.create()
        near_if.up()
        near_if.config_addr()

    def connect_iface_to_port(self, vm_host, iface, port_id):
        near_if_name = vm_host.name + iface.name
        proc = self.ptm.unshare_control('bind_port', self, [near_if_name, port_id])
        stdout, stderr = proc.communicate()
        print "--\n" + stdout + "--\n" + stderr + "=="

    def disconnect_port(self, port_id):
        proc = self.ptm.unshare_control('unbind_port', self, [port_id])
        stdout, stderr = proc.communicate()
        print "--\n" + stdout + "--\n" + stderr + "=="

    def control_start(self):
        if self.num_id == '1':
            pid_file = '/run/midolman/dnsmasq.pid'

            self.cli.cmd('dnsmasq --no-host --no-resolv -S 8.8.8.8')
            dnsm_real_pid = self.cli.cmd("ps -aef | sed -e 's/  */ /g' | grep dnsmasq | cut -d ' ' -f 2")
            print 'dnsmasq PID=' + dnsm_real_pid
            self.cli.rm(pid_file)
            self.cli.write_to_file(pid_file, dnsm_real_pid)

        self.cli.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        process = self.cli.cmd('/usr/share/midolman/midolman-start', blocking=False)
        if process.pid == -1:
            raise SubprocessFailedException('midolman')
        real_pid = self.cli.cmd("ps -aef | sed -e 's/  */ /g' | cut -d ' ' -f 2,3 | awk '{ if ($2==" +
                                str(process.pid) + ") print $1 }'")
        self.cli.write_to_file('/run/midolman/pid', str(real_pid))

    def control_stop(self):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))
            self.cli.rm('/run/midolman/pid')

        if self.num_id == '1':
            pid_file = '/run/midolman/dnsmasq.pid'

            if self.cli.exists(pid_file):
                pid = self.cli.read_from_file(pid_file)
                self.cli.cmd('kill ' + str(pid))
                self.cli.rm(pid_file)

    def control_bind_port(self, near_if_name, port_id):
        print 'binding port ' + port_id + ' to ' + near_if_name
        return self.cli.cmd('mm-ctl --bind-port ' + port_id + ' ' + near_if_name)

    def control_unbind_port(self, port_id):
        return self.cli.cmd('mm-ctl --unbind-port ' + port_id)


class ComputeFileConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(ComputeFileConfiguration, self).__init__()

    def prepare_files(self, num_id, unique_id, zookeeper_ips, cassandra_ips):

        etc_dir = '/etc/midolman.' + num_id
        var_lib_dir = '/var/lib/midolman.' + num_id
        var_log_dir = '/var/lib/midolman.' + num_id
        var_run_dir = '/run/midolman.' + num_id

        self.cli.rm(etc_dir)
        self.cli.copy_dir('/etc/midolman', etc_dir)

        # generates host uuid
        host_uuid = ('# generated for MMM MM $n\n'
                     'host_uuid=') + str(unique_id)
        self.cli.write_to_file(etc_dir + '/host_uuid.properties', host_uuid, False)
        mmconf = etc_dir + '/midolman.conf'

        if len(zookeeper_ips) is not 0:
            z_ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            z_ip_str = ''

        if len(cassandra_ips) is not 0:
            c_ip_str = ','.join([ip.ip for ip in cassandra_ips])
        else:
            c_ip_str = ''

        self.cli.regex_file(mmconf,
                            '/^\[zookeeper\]/,/^$/ s/^zookeeper_hosts =.*$/zookeeper_hosts = ' +
                            z_ip_str + '/')

        self.cli.regex_file(mmconf,
                            '/^\[cassandra\]/,/^$/ '
                            's/^servers =.*$/servers = ' + c_ip_str + '/;'
                            's/^replication_factor =.*$/replication_factor = ' + str(len(cassandra_ips)) + '/')

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
        self.cli.regex_file(mmenv, '/runjdwp/s/1414/141' + num_id + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/65ace0e84265cd777b2855d15fce60148abd9330
        self.cli.regex_file(mmenv, 's/MAX_HEAP_SIZE=.*/MAX_HEAP_SIZE="300M"/')
        self.cli.regex_file(mmenv, 's/HEAP_NEWSIZE=.*/HEAP_NEWSIZE="200M"/')

    def mount_config(self, num_id):
        self.cli.mount('/run/midolman.' + num_id, '/run/midolman')
        self.cli.mount('/var/lib/midolman.' + num_id, '/var/lib/midolman')
        self.cli.mount('/var/log/midolman.' + num_id, '/var/log/midolman')
        self.cli.mount('/etc/midolman.' + num_id, '/etc/midolman')

    def unmount_config(self, num_id):
        self.cli.unmount('/run/midolman.' + num_id)
        self.cli.unmount('/var/lib/midolman')
        self.cli.unmount('/var/log/midolman')
        self.cli.unmount('/etc/midolman')