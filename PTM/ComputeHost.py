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
from os import path
import datetime

import CBT.VersionConfig as version_config

from common.Exceptions import *
from common.IP import IP
from common.CLI import LinuxCLI
from common.FileLocation import *

from ConfigurationHandler import FileConfigurationHandler, ProgramConfigurationHandler
from NetNSHost import NetNSHost
from VMHost import VMHost
from PhysicalTopologyConfig import InterfaceDef, HostDef
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
        if version_config.ConfigMap.get_configured_parameter('option_config_mnconf') is True:
            self.configurator = ComputeMNConfConfiguration()
        else:
            self.configurator = ComputeFileConfiguration()
        self.my_ip = '127.0.0.1'

    def do_extra_config_from_ptc_def(self, cfg, impl_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        implementation-specific configuration
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        :return:
        """

        self.LOG.debug("Individual host configuration for [" + self.name + "]")

        if 'cassandra_ips' in impl_cfg.kwargs:
            for i in impl_cfg.kwargs['cassandra_ips']:
                self.cassandra_ips.append(IP(i))

        if 'zookeeper_ips' in impl_cfg.kwargs:
            for i in impl_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'id' in impl_cfg.kwargs:
            self.num_id = impl_cfg.kwargs['id']

        if u'eth0' in cfg.interfaces:
            self.my_ip = cfg.interfaces[u'eth0'].ip_addresses[0].ip
            self.LOG.debug("Found eth0 in interface cfg with IP[" + self.my_ip + "]")

    def print_config(self, indent=0):
        super(ComputeHost, self).print_config(indent)
        print ('    ' * (indent + 1)) + 'Num-id: ' + self.num_id
        print ('    ' * (indent + 1)) + 'My IP: ' + self.my_ip
        print ('    ' * (indent + 1)) + 'Zookeeper-IPs: ' + ', '.join(str(ip) for ip in self.zookeeper_ips)
        print ('    ' * (indent + 1)) + 'Cassandra-IPs: ' + ', '.join(str(ip) for ip in self.cassandra_ips)
        if len(self.vms) > 0:
            print ('    ' * (indent + 1)) + 'Hosted vms: '
            for vm in self.vms:
                vm.print_config(indent + 2)

    def prepare_config(self):
        self.configurator.configure(self.num_id, self.unique_id, self.zookeeper_ips, self.cassandra_ips)
        self.cli.rm('/etc/midonet_host_id.properties')
        log_dir = '/var/log/midolman.' + self.num_id
        self.ptm.log_manager.add_external_log_file(FileLocation(log_dir + '/midolman.log'), self.num_id,
                                                   '%Y.%m.%d %H:%M:%S.%f')
        self.ptm.log_manager.add_external_log_file(FileLocation(log_dir + '/midolman.event.log'), self.num_id,
                                                   '%Y.%m.%d %H:%M:%S.%f')
        self.ptm.log_manager.add_external_log_file(FileLocation(log_dir + '/mm-trace.log'), self.num_id,
                                                   '%Y.%m.%d %H:%M:%S.%f')

    def do_extra_create_host_cfg_map_for_process_control(self):
        return {'num_id': self.num_id, 'uuid': str(self.unique_id), 'my_ip': self.my_ip,
                'zookeeper_ips': ','.join(str(ip) for ip in self.zookeeper_ips)}

    def do_extra_config_host_for_process_control(self, cfg_map):
        self.num_id = cfg_map['num_id']
        self.my_ip = cfg_map['my_ip']
        self.unique_id = uuid.UUID('urn:uuid:' + cfg_map['uuid'])
        self.zookeeper_ips = [IP.make_ip(s) for s in cfg_map['zookeeper_ips'].split(',')]

    def wait_for_process_start(self):
        retries = 0
        max_retries = 60
        connected = False
        while not connected:
            if self.cli.grep_cmd(version_config.ConfigMap.get_configured_parameter('cmd_list_datapath'), 'midonet') is True:
                connected = True
            else:
                retries += 1
                if retries > max_retries:
                    raise SubprocessFailedException('MidoNet Agent host ' + self.num_id + ' timed out while starting')
                time.sleep(1)

    def wait_for_process_stop(self):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))

            deadline = datetime.datetime.now() + datetime.timedelta(seconds=30)
            while LinuxCLI().is_pid_running(pid):
                if datetime.datetime.now() > deadline:
                    self.LOG.error("Process " + str(pid) + " not stopping, killing with extreme prejudice (kill -9)")
                    self.cli.cmd('kill -9' + str(pid))

                    deadline2 = datetime.datetime.now() + datetime.timedelta(seconds=30)
                    while LinuxCLI().is_pid_running(pid):
                        if datetime.datetime.now() > deadline2:
                            self.LOG.error("Process " + str(pid) + " not stopped, even with SIGKILL")
                            raise SubprocessTimeoutException("Couldn't stop process: midolman")

            self.cli.rm('/run/midolman/pid')

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
        self.LOG.debug('Binding interface: ' + near_if_name + ' to port ID: ' + port_id)
        proc = self.ptm.unshare_control('bind_port', self, [near_if_name, port_id])
        stdout, stderr = proc.communicate()
        self.LOG.debug("--\n" + stdout + "--\n" + stderr + "==")

    def disconnect_port(self, port_id):
        self.LOG.debug('Unbinding port ID: ' + port_id)
        proc = self.ptm.unshare_control('unbind_port', self, [port_id])
        stdout, stderr = proc.communicate()
        self.LOG.debug("--\n" + stdout + "--\n" + stderr + "==")

    def control_start(self):
        if self.num_id == '1':
            this_dir = path.dirname(path.abspath(__file__))

            ret = self.cli.cmd('mn-conf set -t default < ' + this_dir + '/scripts/midolman.mn-conf', return_status=True)
            if ret != 0:
                self.LOG.fatal('\n'.join(self.cli.last_process.stdout.readlines()))
                self.LOG.fatal('\n'.join(self.cli.last_process.stderr.readlines()))
                raise SubprocessFailedException('Failed to run mn-conf with defaults: ' + str(ret))

            ret = self.cli.cmd('mn-conf set -t default < .mnconf.data', return_status=True)
            if ret != 0:
                self.LOG.fatal('\n'.join(self.cli.last_process.stdout.readlines()))
                self.LOG.fatal('\n'.join(self.cli.last_process.stderr.readlines()))
                raise SubprocessFailedException('Failed to run mn-conf: ' + str(ret))

            pid_file = '/run/midolman/dnsmasq.pid'

            self.cli.cmd('dnsmasq --no-host --no-resolv -S 8.8.8.8')
            dnsm_real_pid = self.cli.get_process_pids('dnsmasq')[-1]
            self.LOG.debug('dnsmasq PID=' + dnsm_real_pid)
            self.cli.rm(pid_file)
            self.cli.write_to_file(pid_file, dnsm_real_pid)

        self.cli.cmd('hostname ' + self.name)
        self.cli.add_to_host_file(self.name, self.my_ip)

        self.cli.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        process = self.cli.cmd('/usr/share/midolman/midolman-start', blocking=False)
        if process.pid == -1:
            raise SubprocessFailedException('midolman')
        real_pid = self.cli.get_parent_pids(process.pid)[-1]
        self.cli.write_to_file('/run/midolman/pid', str(real_pid))

    def control_stop(self):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))

        if self.num_id == '1':
            pid_file = '/run/midolman/dnsmasq.pid'

            if self.cli.exists(pid_file):
                pid = self.cli.read_from_file(pid_file)
                self.cli.cmd('kill ' + str(pid))
                self.cli.rm(pid_file)

            self.cli.rm('.mnconf.data')

    def control_bind_port(self, near_if_name, port_id):
        self.LOG.debug('binding port ' + port_id + ' to ' + near_if_name)
        return self.cli.cmd('mm-ctl --bind-port ' + port_id + ' ' + near_if_name)

    def control_unbind_port(self, port_id):
        return self.cli.cmd('mm-ctl --unbind-port ' + port_id)


class ComputeMNConfConfiguration(ProgramConfigurationHandler):

    def configure(self, num_id, unique_id, zookeeper_ips, cassandra_ips):
        etc_dir = '/etc/midolman.' + num_id
        var_lib_dir = '/var/lib/midolman.' + num_id
        var_log_dir = '/var/log/midolman.' + num_id
        var_run_dir = '/run/midolman.' + num_id

        if len(zookeeper_ips) is not 0:
            z_ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            z_ip_str = ''

        midonet_key = '/midonet/v1' \
            if version_config.ConfigMap.get_configured_parameter('option_use_v2_stack') is False \
            else '/midonet/v2'

        self.cli.rm(etc_dir)
        self.cli.copy_dir('/etc/midolman', etc_dir)

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir)

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)

        self.cli.mkdir('/run/midolman')
        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)

        mmenv = etc_dir + '/midolman-env.sh'
        mmconf = etc_dir + '/midolman.conf'

        self.cli.write_to_file(mmconf,
                               '[zookeeper]\n'
                               'zookeeper_hosts = ' + z_ip_str + '\n'
                               'root_key = ' + midonet_key + '\n')

        # Allow connecting via debugger - MM 1 listens on 1411, MM 2 on 1412, MM 3 on 1413
        self.cli.regex_file(mmenv, '/runjdwp/s/^..//g')
        self.cli.regex_file(mmenv, '/runjdwp/s/1414/141' + num_id + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/65ace0e84265cd777b2855d15fce60148abd9330
        self.cli.regex_file(mmenv, 's/MAX_HEAP_SIZE=.*/MAX_HEAP_SIZE="300M"/')
        self.cli.regex_file(mmenv, 's/HEAP_NEWSIZE=.*/HEAP_NEWSIZE="200M"/')

        self.cli.rm('/etc/midonet_host_id.properties')
        uuid_str = 'host_uuid=' + str(unique_id) + '\n'
        self.cli.write_to_file(etc_dir + '/host_uuid.properties', uuid_str)

        if not self.cli.exists('.mnconf.data'):
            if len(cassandra_ips) is not 0:
                c_ip_str = ','.join([ip.ip for ip in cassandra_ips])
            else:
                c_ip_str = ''

            bgpd_program = "/usr/lib/quagga" if self.cli.os_name() == 'ubuntu' else "/usr/sbin"
            mn_conf_str = ('zookeeper {\n'
                           '  zookeeper_hosts : "' + z_ip_str + '"\n'
                           '}\n'
                           'cassandra {\n'
                           '  servers : "' + c_ip_str + '"\n'
                           '  replication_factor : ' + str(len(cassandra_ips)) + '\n'
                           '  send_buffer_pool_buf_size_kb : 10\n'
                           '  haproxy_health_monitor : true\n'
                           '}\n'
                           'agent {\n'
                           '  midolman {\n'
                           '    bgpd_binary : "' + bgpd_program + '"\n'
                           '  }\n'
                           '  loggers {\n'
                           '    root=DEBUG\n'
                           '  }\n'
                           '}\n')

            self.cli.write_to_file('.mnconf.data', mn_conf_str)

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

class ComputeFileConfiguration(FileConfigurationHandler):
    def configure(self, num_id, unique_id, zookeeper_ips, cassandra_ips):

        etc_dir = '/etc/midolman.' + num_id
        var_lib_dir = '/var/lib/midolman.' + num_id
        var_log_dir = '/var/lib/midolman.' + num_id
        var_run_dir = '/run/midolman.' + num_id

        self.cli.rm(etc_dir)
        self.cli.copy_dir('/etc/midolman', etc_dir)

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

        # Allow connecting via debugger - MM 1 listens on 1411, MM 2 on 1412, MM 3 on 1413, ...
        self.cli.regex_file(mmenv, '/runjdwp/s/^..//g')
        self.cli.regex_file(mmenv, '/runjdwp/s/1414/141' + num_id + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/65ace0e84265cd777b2855d15fce60148abd9330
        self.cli.regex_file(mmenv, 's/MAX_HEAP_SIZE=.*/MAX_HEAP_SIZE="300M"/')
        self.cli.regex_file(mmenv, 's/HEAP_NEWSIZE=.*/HEAP_NEWSIZE="200M"/')

        self.cli.rm('/etc/midonet_host_id.properties')
        uuid_str = 'host_uuid=' + str(unique_id) + '\n'
        self.cli.write_to_file(etc_dir + '/host_uuid.properties', uuid_str)

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
