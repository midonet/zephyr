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

import datetime
from os import path
import time
import uuid

from zephyr.common.cli import LinuxCLI
from zephyr.common import exceptions
from zephyr.common.file_location import FileLocation
from zephyr.common.ip import IP
from zephyr.midonet import midonet_mm_ctl
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.application import configuration_handler
from zephyr_ptm.ptm.config import version_config
from zephyr_ptm.ptm.physical_topology_config import HostDef
from zephyr_ptm.ptm import ptm_constants


class Midolman(application.Application):
    @staticmethod
    def get_name():
        return 'midolman'

    @staticmethod
    def get_type():
        return application.APPLICATION_TYPE_NETWORK_OVERLAY

    """
    Implements the HypervisorHost contract to create VMs
    """
    def __init__(self, host, app_id=''):
        super(Midolman, self).__init__(host, app_id)
        self.vms = {}
        """ :type: dict[str, VMHost]"""
        self.num_id = ''
        self.zookeeper_ips = []
        self.cassandra_ips = []
        self.hv_active = True

        self.config_dir = '/etc/midolman'
        self.lib_dir = '/var/lib/midolman'
        self.log_dir = '/var/log/midolman'
        self.runtime_dir = '/run/midolman'

        if version_config.ConfigMap.get_configured_parameter(
                'option_config_mnconf') is True:
            self.configurator = ComputeMNConfConfiguration()
        else:
            self.configurator = ComputeFileConfiguration()
        self.my_ip = '127.0.0.1'

    def get_resource(self, resource_name, **kwargs):
        """
        Resource Type | Return Type
        --------------+--------------------------------
        log           | log file as a STRING
        fwaas_log     | if "uuid" is provided, specific log as a STRING
                      | if "uuid" is not provided, map of
                      |     filename -> contents as a STRING

        """
        if resource_name == 'log':
            # TODO(micucci) Use an SSH accessor here if this app is
            # on a remote host
            self.LOG.debug("Fetching log from: " +
                           self.log_dir + "/midolman.log")
            floc = FileLocation(self.log_dir + '/midolman.log')
            return floc.fetch_file()
        elif resource_name == 'fwaas_log':
            if 'uuid' not in kwargs:
                # Get ALL firewall logs as a dict of filename -> contents
                files = {}
                fwaas_logs = LinuxCLI().ls('firewall-*.log')
                for log in fwaas_logs:
                    floc = FileLocation(log)
                    self.LOG.debug("Fetching fwaas log from: " +
                                   log)
                    files[floc.filename] = floc.fetch_file()
                return files
            else:
                log_name = (self.log_dir + '/firewall-' +
                            str(kwargs['uuid']) + '.log')
                self.LOG.debug("Fetching fwaas log from: " +
                               log_name)
                floc = FileLocation(log_name)
            return floc.fetch_file()
        return None

    def configure(self, host_cfg, app_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        app-specific configuration
        :type host_cfg: HostDef
        :type app_cfg: ApplicationDef
        :return:
        """
        self.LOG.debug("Midolman app configuration for [" +
                       host_cfg.name + "]")

        if 'cassandra_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['cassandra_ips']:
                self.cassandra_ips.append(IP(i))

        if 'zookeeper_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'hypervisor' in app_cfg.kwargs:
            self.hv_active = app_cfg.kwargs['hypervisor']

        if 'id' in app_cfg.kwargs:
            self.num_id = str(app_cfg.kwargs['id'])

        self.my_ip = self.host.main_ip
        self.LOG.debug("Found host IP[" + self.my_ip + "]")

        subdir = '.' + self.num_id if self.num_id != '' else ''
        self.config_dir = '/etc/midolman' + subdir
        self.lib_dir = '/var/lib/midolman' + subdir
        self.log_dir = '/var/log/midolman' + subdir
        self.runtime_dir = '/run/midolman' + subdir

        if self.cli.exists(self.config_dir + '/host_uuid.properties'):
            self.unique_id = self.cli.read_from_file(
                self.config_dir + "/host_uuid.properties").replace(
                'host_uuid=', '').strip()
        else:
            self.unique_id = uuid.uuid4()

        log_dir = '/var/log/midolman' + subdir
        self.host.log_manager.add_external_log_file(
            FileLocation(log_dir + '/midolman.log'), self.num_id,
            '%Y.%m.%d %H:%M:%S.%f')

    def print_config(self, indent=0):
        super(Midolman, self).print_config(indent)
        print(('    ' * (indent + 1)) + 'Num-id: ' + self.num_id)
        print(('    ' * (indent + 1)) + 'My IP: ' + self.my_ip)
        print(('    ' * (indent + 1)) + 'Zookeeper-IPs: ' +
              ', '.join(str(ip) for ip in self.zookeeper_ips))
        print(('    ' * (indent + 1)) + 'Cassandra-IPs: ' +
              ', '.join(str(ip) for ip in self.cassandra_ips))
        if len(self.vms) > 0:
            print(('    ' * (indent + 1)) + 'Hosted vms: ')
            for vm in self.vms.itervalues():
                vm.print_config(indent + 2)

    def prepare_config(self, log_manager):
        self.configurator.configure(self.num_id, self.unique_id,
                                    self.zookeeper_ips, self.cassandra_ips)
        self.cli.rm('/etc/midonet_host_id.properties')

    def create_cfg_map(self):
        return {'num_id': self.num_id,
                'uuid': str(self.unique_id),
                'my_ip': self.my_ip,
                'zookeeper_ips': ','.join(str(ip)
                                          for ip in self.zookeeper_ips)}

    def config_app_for_process_control(self, cfg_map):
        self.num_id = cfg_map['num_id']
        self.my_ip = cfg_map['my_ip']
        self.unique_id = uuid.UUID('urn:uuid:' + cfg_map['uuid'])
        self.zookeeper_ips = [IP.make_ip(s)
                              for s in cfg_map['zookeeper_ips'].split(',')]

    def wait_for_process_start(self):
        retries = 0
        max_retries = ptm_constants.APPLICATION_START_TIMEOUT
        connected = False
        while not connected:
            if self.cli.grep_cmd(
                    version_config.ConfigMap.get_configured_parameter(
                        'cmd_list_datapath'), 'midonet') is True:
                connected = True
            else:
                retries += 1
                if retries > max_retries:
                    raise exceptions.SubprocessFailedException(
                        'MidoNet Agent host ' + self.num_id +
                        ' timed out while starting')
                time.sleep(1)

    def wait_for_process_stop(self):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))

            deadline = datetime.datetime.now() + datetime.timedelta(seconds=30)
            while LinuxCLI().is_pid_running(pid):
                if datetime.datetime.now() > deadline:
                    self.LOG.error(
                        "Process " + str(pid) +
                        " not stopping, killing with extreme prejudice "
                        "(kill -9)")
                    self.cli.cmd('kill -9' + str(pid))

                    deadline2 = (datetime.datetime.now() +
                                 datetime.timedelta(seconds=30))
                    while LinuxCLI().is_pid_running(pid):
                        if datetime.datetime.now() > deadline2:
                            self.LOG.error(
                                "Process " + str(pid) +
                                " not stopped, even with SIGKILL")
                            raise exceptions.SubprocessTimeoutException(
                                "Couldn't stop process: midolman")

            self.cli.rm('/run/midolman/pid')

    def prepare_environment(self):
        self.configurator.mount_config(self.num_id)

    def cleanup_environment(self):
        self.configurator.unmount_config(self.num_id)

    @staticmethod
    def is_virtual_network_host():
        return True

    def connect_iface_to_port(self, vm_host_name, iface, port_id):
        near_if_name = vm_host_name + iface
        self.LOG.debug('Binding interface: ' + near_if_name +
                       ' to port ID: ' + port_id)
        midonet_mm_ctl.bind_port(
            mn_api_url=version_config.ConfigMap.get_configured_parameter(
                'param_midonet_api_url'),
            host_id=str(self.unique_id),
            port_id=port_id,
            interface_name=near_if_name)

    def disconnect_port(self, port_id):
        self.LOG.debug('Unbinding port ID: ' + port_id)
        try:
            midonet_mm_ctl.unbind_port(
                mn_api_url=version_config.ConfigMap.get_configured_parameter(
                    'param_midonet_api_url'),
                host_id=str(self.unique_id),
                port_id=port_id)
        except exceptions.ObjectNotFoundException as e:
            self.LOG.error('Exception unbinding port: ' + str(e))

    def control_start(self):
        if self.num_id == '1' or self.num_id == '':
            if self.cli.exists('.mnconf.data'):
                this_dir = path.dirname(path.abspath(__file__))

                ret = self.cli.cmd('mn-conf set -t default < ' +
                                   this_dir + '/../scripts/midolman.mn-conf')
                if ret.ret_code != 0:
                    self.LOG.fatal(ret.stdout)
                    self.LOG.fatal(ret.stderr)
                    raise exceptions.SubprocessFailedException(
                        'Failed to run mn-conf with defaults: ' + str(ret))

                ret = self.cli.cmd('mn-conf set -t default < .mnconf.data')
                if ret.ret_code != 0:
                    self.LOG.fatal(ret.stdout)
                    self.LOG.fatal(ret.stderr)
                    raise exceptions.SubprocessFailedException(
                        'Failed to run mn-conf: ' + str(ret))

            pid_file = '/run/midolman/dnsmasq.pid'

            self.cli.cmd('dnsmasq --no-host --no-resolv -S 8.8.8.8')
            dnsm_real_pid = self.cli.get_process_pids('dnsmasq')[-1]
            self.LOG.debug('dnsmasq PID=' + dnsm_real_pid)
            self.cli.rm(pid_file)
            self.cli.write_to_file(pid_file, dnsm_real_pid)

        self.cli.cmd('hostname ' + self.host.proxy_name)
        self.cli.add_to_host_file(self.host.proxy_name, self.my_ip)

        self.cli.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        process = self.cli.cmd(
            '/usr/share/midolman/midolman-start', blocking=False).process
        if process.pid == -1:
            raise exceptions.SubprocessFailedException('midolman')
        real_pid = self.cli.get_parent_pids(process.pid)[-1]
        self.cli.write_to_file(self.runtime_dir + '/pid', str(real_pid))

    def control_stop(self):
        if self.cli.exists('/run/midolman/pid'):
            pid = self.cli.read_from_file('/run/midolman/pid')
            self.cli.cmd('kill ' + str(pid))

        if self.num_id == '1' or self.num_id == '':
            pid_file = '/run/midolman/dnsmasq.pid'

            if self.cli.exists(pid_file):
                pid = self.cli.read_from_file(pid_file)
                self.cli.cmd('kill ' + str(pid))
                self.cli.rm(pid_file)

            self.cli.rm('.mnconf.data')


# noinspection PyUnresolvedReferences
class ComputeMNConfConfiguration(
        configuration_handler.ProgramConfigurationHandler):

    def configure(self, num_id, unique_id, zookeeper_ips, cassandra_ips):
        subdir = '.' + num_id if num_id != '' else ''
        etc_dir = '/etc/midolman' + subdir
        var_lib_dir = '/var/lib/midolman' + subdir
        var_log_dir = '/var/log/midolman' + subdir
        var_run_dir = '/run/midolman' + subdir

        if len(zookeeper_ips) is not 0:
            z_ip_str = ','.join([ip.ip + ':2181' for ip in zookeeper_ips])
        else:
            z_ip_str = ''

        if num_id != '':
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
        mn_central_conf = '/etc/midonet/midonet.conf'

        self.cli.write_to_file(mmconf,
                               '[zookeeper]\n'
                               'zookeeper_hosts = ' + z_ip_str + '\n')

        self.cli.write_to_file(mn_central_conf,
                               '[zookeeper]\n'
                               'zookeeper_hosts = ' + z_ip_str + '\n')

        # Allow connecting via debugger - MM 1 listens on 1411, MM 2 on 1412,
        # MM 3 on 1413
        self.cli.regex_file(mmenv, '/runjdwp/s/^# //g')
        self.cli.regex_file(mmenv, '/runjdwp/s/141[0-9]/141' +
                                   (num_id if num_id != '' else '0') + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/
        # 65ace0e84265cd777b2855d15fce60148abd9330
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

            bgpd_program = ("/usr/lib/quagga"
                            if self.cli.os_name() == 'ubuntu'
                            else "/usr/sbin")
            mn_conf_str = (
                'zookeeper {\n'
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
        subdir = '.' + num_id if num_id != '' else ''
        etc_dir = '/etc/midolman' + subdir
        var_lib_dir = '/var/lib/midolman' + subdir
        var_log_dir = '/var/log/midolman' + subdir
        var_run_dir = '/run/midolman' + subdir
        self.cli.mount(var_run_dir, '/run/midolman')
        self.cli.mount(var_lib_dir, '/var/lib/midolman')
        self.cli.mount(var_log_dir, '/var/log/midolman')
        self.cli.mount(etc_dir, '/etc/midolman')

    def unmount_config(self, num_id):
        subdir = '.' + num_id if num_id != '' else ''
        var_run_dir = '/run/midolman' + subdir
        self.cli.unmount(var_run_dir)
        self.cli.unmount('/var/lib/midolman')
        self.cli.unmount('/var/log/midolman')
        self.cli.unmount('/etc/midolman')


class ComputeFileConfiguration(configuration_handler.FileConfigurationHandler):
    def configure(self, num_id, unique_id, zookeeper_ips, cassandra_ips):

        subdir = '.' + num_id if num_id != '' else ''
        etc_dir = '/etc/midolman' + subdir
        var_lib_dir = '/var/lib/midolman' + subdir
        var_log_dir = '/var/log/midolman' + subdir
        var_run_dir = '/run/midolman' + subdir

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

        self.cli.regex_file(
            mmconf,
            '/^\[zookeeper\]/,/^$/ s/^zookeeper_hosts =.*$'
            '/zookeeper_hosts = ' +
            z_ip_str + '/')

        self.cli.regex_file(
            mmconf,
            '/^\[cassandra\]/,/^$/ '
            's/^servers =.*$/servers = ' + c_ip_str + '/;'
            's/^replication_factor =.*$/replication_factor = ' +
            str(len(cassandra_ips)) + '/')

        self.cli.regex_file(
            mmconf,
            ('/^\[midolman\]/,/^\[/ s%^[# ]*bgpd_binary = '
             '/usr/lib/quagga.*$%bg'
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
        self.cli.regex_file(lb,
                            's/rolling.RollingFileAppender/FileAppender/g')

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir)

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)

        self.cli.mkdir('/run/midolman')
        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)

        mmenv = etc_dir + '/midolman-env.sh'

        # Allow connecting via debugger - MM 1 listens on 1411, MM 2 on 1412,
        # MM 3 on 1413, ...
        self.cli.regex_file(mmenv, '/runjdwp/s/^# //g')
        self.cli.regex_file(mmenv, '/runjdwp/s/141[0-9]/141' +
                                   (num_id if num_id != '' else '0') + '/g')

        # Setting memory to the ones before
        # https://github.com/midokura/midonet/commit/
        # 65ace0e84265cd777b2855d15fce60148abd9330
        self.cli.regex_file(mmenv, 's/MAX_HEAP_SIZE=.*/MAX_HEAP_SIZE="300M"/')
        self.cli.regex_file(mmenv, 's/HEAP_NEWSIZE=.*/HEAP_NEWSIZE="200M"/')

        self.cli.rm('/etc/midonet_host_id.properties')
        uuid_str = 'host_uuid=' + str(unique_id) + '\n'
        self.cli.write_to_file(etc_dir + '/host_uuid.properties', uuid_str)

    def mount_config(self, num_id):
        subdir = '.' + num_id if num_id != '' else ''
        etc_dir = '/etc/midolman' + subdir
        var_lib_dir = '/var/lib/midolman' + subdir
        var_log_dir = '/var/log/midolman' + subdir
        var_run_dir = '/run/midolman' + subdir
        self.cli.mount(var_run_dir, '/run/midolman')
        self.cli.mount(var_lib_dir, '/var/lib/midolman')
        self.cli.mount(var_log_dir, '/var/log/midolman')
        self.cli.mount(etc_dir, '/etc/midolman')

    def unmount_config(self, num_id):
        subdir = '.' + num_id if num_id != '' else ''
        var_run_dir = '/run/midolman' + subdir
        self.cli.unmount(var_run_dir)
        self.cli.unmount('/var/lib/midolman')
        self.cli.unmount('/var/log/midolman')
        self.cli.unmount('/etc/midolman')
