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
import json
import logging
import time
import uuid
from zephyr.common.cli import LinuxCLI
from zephyr.common.echo_server import DEFAULT_ECHO_PORT
from zephyr.common.echo_server import TERMINATION_STRING
from zephyr.common.exceptions import ArgMismatchException
from zephyr.common.exceptions import SubprocessFailedException
from zephyr.common.exceptions import SubprocessTimeoutException
from zephyr.common.ip import IP
from zephyr.common.tcp_dump import TCPDump
from zephyr.common.tcp_sender import TCPSender
from zephyr.common.utils import get_class_from_fqn
from zephyr.common.utils import terminate_process
from zephyr.ptm.host.bridge import Bridge
from zephyr.ptm.host.interface import Interface
from zephyr.ptm.host.virtual_interface import VirtualInterface
from zephyr.ptm.physical_topology_config import *
from zephyr.ptm.ptm_constants import HOST_CONTROL_CMD_NAME
from zephyr.ptm.ptm_constants import ZEPHYR_LOG_FILE_NAME
from zephyr.ptm.ptm_object import PTMObject

ECHO_SERVER_TIMEOUT = 3

# TODO(micucci): Extrapolate the host access from the host operations
# So we can have IPNetNSHost and "VMSSHHost", etc. and also have
# Cassandra, etc. which supports Cassandra functionality but using
# a flexible accessor so it can run on IPNetNS or VMSSH, etc. without
# having to do multiple inheritance.
# TODO(micucci): [PRIORITY] Furthermore, we should extrapolate all
# process control completely, as the boot and network characterization
# of a host is only superficially linked to the process and its attendant
# configuration which will be running on it.  We should really only
# have a small number of host types, with many processes that can
# run on any kind of host.  This will help resolve the above issue
# as well.


class Host(PTMObject):
    def __init__(self, name, ptm, cli=LinuxCLI(),
                 host_create_func=None, host_remove_func=None):
        super(Host, self).__init__(name, cli)
        self.ptm = ptm
        """ :type: PhysicalTopologyManager"""
        self.bridges = {}
        """ :type: dict[str, Bridge]"""
        self.interfaces = {}
        """ :type: dict[str, Interface]"""
        self.create_func = host_create_func
        """ :type: lambda"""
        self.remove_func = host_remove_func
        """ :type: lambda"""
        self.LOG = logging.getLogger('ptm-null-root')
        """ :type: logging.Logger"""
        self.packet_captures = {}
        """ :type: dict[str, TCPDump]"""
        self.log_manager = (self.ptm.log_manager
                            if self.ptm is not None
                            else None)
        """ :type LogManager"""
        self.applications = []
        """ :type: list[zephyr.ptm.application.application.Application]"""
        self.ip_forward_rules = []
        """ :type: list[(str, str)]"""
        self.route_rules = []
        """ :type: list[(IP, IP, str)]"""
        self.debug = False
        """ :type bool"""
        self.log_level = logging.INFO
        self.echo_server_procs = {}
        """ :type: dict[int, CommandStatus]"""
        self.on_namespace = False

    def configure_logging(self, debug=False,
                          log_file_name=ZEPHYR_LOG_FILE_NAME):
        self.log_level = logging.DEBUG if debug is True else logging.INFO
        self.debug = debug
        msec = int(datetime.datetime.utcnow().microsecond / 1000)
        logname = (self.name + '.' +
                   datetime.datetime.utcnow().strftime('%H%M%S') +
                   '.' + str(msec))
        if debug is True:
            self.LOG = self.log_manager.add_tee_logger(
                file_name=log_file_name,
                name=logname + '-debug',
                file_log_level=self.log_level,
                stdout_log_level=self.log_level)
            self.LOG.info("Turning on debug logs")
        else:
            self.LOG = self.log_manager.add_file_logger(
                file_name=log_file_name,
                name=logname,
                log_level=self.log_level)

    def config_from_ptc_def(self, cfg, impl_cfg):
        """
        Configure from the given Physical Topology Config definition
        (in this case, a HostDef), and the implementation-specific
        configuration which can contain specific arguments
        :type cfg: HostDef
        :type impl_cfg: ImplementationDef
        :return:
        """
        bridges = cfg.bridges if cfg.bridges else {}
        """ :type: dict [str, BridgeDef]"""
        interfaces = cfg.interfaces if cfg.interfaces else {}
        """ :type: dict [str, InterfaceDef]"""
        ip_rules = cfg.ip_forward_rules if cfg.ip_forward_rules else []
        """ :type list [IPForwardRuleDef]"""
        route_rules = cfg.route_rules if cfg.route_rules else []
        """ :type list [RouteRuleDef]"""
        self.name = cfg.name

        # Configure bridges now, but hold off on interfaces until
        # we get to wiring
        for name, br in bridges.iteritems():
            b = Bridge(name, self, br.mac_address, br.ip_addresses, br.options)
            self.bridges[name] = b

        for iface in interfaces.itervalues():
            link_br = None
            if iface.linked_bridge is not None:
                if iface.linked_bridge not in self.bridges:
                    raise ObjectNotFoundException(
                        'Linked bridge ' + iface.linked_bridge +
                        ' on interface not found on host ' + self.name)

                link_br = self.bridges[iface.linked_bridge]

            # Set up an interface here, but it will be replaced by
            # a virtual interface if this host/interface is defined as a
            # near-pair in a wiring config
            self.interfaces[iface.name] = Interface(
                iface.name, self, iface.mac_address,
                iface.ip_addresses, link_br, iface.vlans)

        for ip_rule in ip_rules:
            self.ip_forward_rules.append((ip_rule.exterior, ip_rule.interior))

        for route in route_rules:
            self.route_rules.append((route.dest, route.gw, route.dev))

        # Configure the host with all of the apps it will be running
        for app_cfg in impl_cfg.apps:
            # Module name is the whole string, while class name is the
            # last name after the last dot (.)
            self.LOG.debug('Configuring host: ' + self.name +
                           ' with application: ' + app_cfg.class_name)
            app_class = get_class_from_fqn(app_cfg.class_name)
            app_id = uuid.uuid4()
            a = app_class(self, app_id)
            """ :type: zephyr.ptm.application.application.Application"""
            a.configure(cfg, app_cfg)
            a.configure_logging(debug=self.debug)
            self.applications.append(a)

    def create_cfg_map(self):
        pass

    def create_host_cfg_map_for_process_control(self):
        """
        Returns a map representing this object in order to
        start/stop the host process.
        """
        cfg_map = {
            'name': self.name,
            'impl': self.__module__ + "." + self.__class__.__name__}
        return cfg_map

    def link_interface(self, near_interface, far_host, far_interface):
        """
        Configure a link using a VirtualInterface between this
        host/interface pair and the far end host/interface pair.
        :type near_interface: Interface
        :type far_host: Host
        :type far_interface: Interface
        :return:
        """
        self.LOG.debug('Linking interface ' + near_interface.name +
                       ' on ' + self.name + ' to far host: ' +
                       far_host.name + '/' + far_interface.name)
        # Create the Virtual Interface
        new_if = VirtualInterface(
            name=near_interface.name, host=near_interface.host,
            mac=near_interface.mac, ip_addr=near_interface.ip_list,
            linked_bridge=near_interface.linked_bridge,
            vlans=near_interface.vlans, far_interface=far_interface,
            use_namespace=far_host.on_namespace)

        self.interfaces[new_if.name] = new_if

    def set_log_level(self, level):
        self.LOG.setLevel(level)

    def create(self):
        if self.create_func is not None:
            self.create_func(self.name)

    def remove(self):
        if self.remove_func is not None:
            self.remove_func(self.name)

    def boot(self):
        # Create and bring up all bridges since they are local
        for bridge in self.bridges.values():
            self.LOG.debug('Creating and bringing up bridge: ' + bridge.name)
            bridge.create()
            bridge.config_addr()
            bridge.up()

        # Create all interfaces, but wait to bring them up
        for interface in self.interfaces.itervalues():
            self.LOG.debug('Creating interface: ' + interface.name)
            interface.create()

        self.set_loopback()

    def shutdown(self):
        for interface in self.interfaces.itervalues():
            interface.remove()

        for bridge in self.bridges.itervalues():
            bridge.remove()

    def reboot(self):
        self.shutdown()
        self.boot()

    def net_up(self):
        # Configure and bring up all network 'devices'
        for interface in self.interfaces.itervalues():
            self.LOG.debug('Bringing up interface: ' + interface.name +
                           ' and configuring addresses: ' +
                           str(map(str, interface.ip_list)))
            interface.up()
            interface.config_addr()
            interface.start_vlans()

    def net_finalize(self):
        # Special for VETH pairs, set the peer's default route to this host's
        # bridge if a) it is present and b) it has IP addresses
        for interface in self.interfaces.itervalues():
            if isinstance(interface, VirtualInterface):
                """ :type interface: VirtualInterface"""
                interface.add_peer_route()

        # Set up any IP forward rules
        for exterior, interior in self.ip_forward_rules:
            self.cli.cmd('iptables -t nat -A POSTROUTING -o ' +
                         exterior + ' -j MASQUERADE')
            self.cli.cmd('/sbin/iptables -A FORWARD -i ' +
                         interior + ' -o ' + exterior + ' -j ACCEPT')
            self.cli.cmd('/sbin/iptables -A FORWARD -i ' +
                         exterior + ' -o ' + interior +
                         ' -m state --state RELATED,ESTABLISHED -j ACCEPT')

        # Set up any IP forward rules
        for dest, gw, dev in self.route_rules:
            self.add_route(dest, gw, dev)

    def net_down(self):
        # Set up any IP forward rules
        for dest, gw, dev in self.route_rules:
            self.del_route(dest)

        # Set up any IP forward rules
        for exterior, interior in self.ip_forward_rules:
            self.cli.cmd('iptables -t nat -D POSTROUTING -o ' +
                         exterior + ' -j MASQUERADE')
            self.cli.cmd('/sbin/iptables -D FORWARD -i ' +
                         interior + ' -o ' + exterior + ' -j ACCEPT')
            self.cli.cmd('/sbin/iptables -D FORWARD -i ' +
                         exterior + ' -o ' + interior +
                         ' -m state --state RELATED,ESTABLISHED -j ACCEPT')

        for interface in self.interfaces.itervalues():
            interface.stop_vlans()
            interface.down()

        for bridge in self.bridges.itervalues():
            bridge.down()

    def prepare_applications(self, lm):
        for app in self.applications:
            app.prepare_config(lm)

    def start_applications(self):
        for app in self.applications:
            self.LOG.debug('ptm starting app: ' + app.name)
            start_process = self.run_app_command('start', app)
            stdout, stderr = start_process.communicate()
            start_process.poll()
            # if start_process.returncode != 0:
            self.LOG.debug("Host control process output: ")
            self.LOG.debug(stdout)
            self.LOG.debug("Host control process error output: ")
            self.LOG.debug(stderr)

    def wait_for_all_applications_to_start(self):
        for app in self.applications:
            app.wait_for_process_start()

    def stop_applications(self):
        for app in self.applications:
            self.LOG.debug('ptm stopping app: ' + app.name)
            stop_process = self.run_app_command('stop', app)
            stdout, stderr = stop_process.communicate()
            stop_process.poll()
            # if stop_process.returncode != 0:
            self.LOG.debug("Host control process output: ")
            self.LOG.debug(stdout)
            self.LOG.debug("Host control process error output: ")
            self.LOG.debug(stderr)

    def wait_for_all_applications_to_stop(self):
        for app in self.applications:
            app.wait_for_process_stop()

    def set_loopback(self, ip=IP('127.0.0.1', '8')):
        if not self.cli.grep_cmd('ip addr | grep lo | grep inet', str(ip)):
            self.cli.cmd('ip addr add ' + str(ip) + ' dev lo')
        self.cli.cmd('ip link set dev lo up')

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        """
        :type route_ip: IP
        :type gw_ip: IP
        :type dev: str
        :return:
        """
        if gw_ip is None:
            if dev is None:
                raise ArgMismatchException(
                    'Must specify either next-hop GW or device to add a route')
            self.cli.cmd('ip route add ' + str(route_ip) + ' dev ' + str(dev))
        else:
            self.cli.cmd('ip route add ' + str(route_ip) + ' via ' + gw_ip.ip +
                         (' dev ' + str(dev) if dev else ''))

    def del_route(self, route_ip):
        self.cli.cmd('ip route del ' + str(route_ip.ip))

    def print_config(self, indent=0):
        print(('    ' * indent) + self.name + ": Impl class " +
              self.__class__.__name__)
        if self.bridges is not None and len(self.bridges) > 0:
            print(('    ' * (indent + 1)) + '[bridges]')
            for b in self.bridges.itervalues():
                b.print_config(indent + 2)
        if self.route_rules is not None and len(self.route_rules) > 0:
            print(('    ' * (indent + 1)) + '[routes]')
            for dest, gw, dev in self.route_rules:
                print(('    ' * (indent + 2)) + 'to ' + str(dest) +
                      ' via ' + str(gw) + ' on ' + dev)
        if self.interfaces is not None and len(self.interfaces) > 0:
            print(('    ' * (indent + 1)) + '[interfaces]')
            for i in self.interfaces.itervalues():
                i.print_config(indent + 2)
        if self.interfaces is not None and len(self.interfaces) > 0:
            print(('    ' * (indent + 1)) + '[applications]')
            for i in self.applications:
                i.print_config(indent + 2)

    def run_app_command(self, command, app, arg_list=list()):
        host_cfg_str = (json.dumps(
            self.create_host_cfg_map_for_process_control()).replace(
            '"', '\\"'))
        app_cfg_str = (json.dumps(
            app.create_app_cfg_map_for_process_control()).replace(
            '"', '\\"'))
        cmd = ('unshare --mount --uts -- /bin/bash -x -c -- '
               '"PYTHONPATH=' + self.ptm.root_dir + ' python ' +
               self.ptm.root_dir + '/' + HOST_CONTROL_CMD_NAME +
               ' -c ' + command +
               " -j '" + host_cfg_str +
               "' -a '" + app_cfg_str +
               "' -l " + self.ptm.log_manager.root_dir + " " +
               ' '.join(arg_list) + '"')

        return LinuxCLI().cmd(cmd, blocking=False).process

    def start_echo_server(self, ip='localhost', port=DEFAULT_ECHO_PORT,
                          echo_data="echo-reply", protocol='tcp'):
        """
        Start an echo server listening on given ip/port (default to
        localhost:80) which returns the echo_data on any TCP
        connection made to the port.
        :param ip: str
        :param port: int
        :param echo_data: str
        :param protocol: str
        :return: CommandStatus
        """
        if (port in self.echo_server_procs and
                self.echo_server_procs[port] is not None):
            self.stop_echo_server(ip, port)
        proc_name = self.ptm.root_dir + '/echo-server.py'
        self.LOG.debug('Starting echo server: ' + proc_name + ' on: ' +
                       ip + ':' + str(port))
        cmd0 = [proc_name,
                '-i', ip,
                '-p', str(port),
                '-d', echo_data,
                '-r', protocol]
        proc = self.cli.cmd_pipe(commands=[cmd0], blocking=False)
        timeout = time.time() + ECHO_SERVER_TIMEOUT

        conn_resp = ''
        while conn_resp != 'connect-test:' + echo_data:
            proc.process_array[0].poll()
            if proc.process_array[0].returncode is not None:
                out, err = proc.process.communicate()
                self.LOG.error('Error starting echo server: ' +
                               str(out) + '/' + str(err))
                raise SubprocessFailedException(
                    'Error starting echo server: ' + str(out) + '/' + str(err))
            if time.time() > timeout:
                raise SubprocessTimeoutException(
                    'Echo server listener failed to bind to port '
                    'within timeout')
            conn_resp = self.send_echo_request(dest_ip=ip, dest_port=port,
                                               echo_request='connect-test',
                                               protocol=protocol)

        self.echo_server_procs[port] = proc
        return proc

    def stop_echo_server(self, ip='localhost', port=DEFAULT_ECHO_PORT):
        """
        Stop an echo server that has been started on given ip/port (defaults to
        localhost:80).  If echo service has not been started, do nothing.
        :param ip: str
        :param port: int
        :return:
        """
        if (port in self.echo_server_procs and
                self.echo_server_procs[port] is not None):
            self.LOG.debug('Stopping echo server on: ' + ip + ':' + str(port))
            proc = self.echo_server_procs[port]
            proc.process_array[0].poll()
            terminate_process(proc.process, signal='TERM')

            timeout = time.time() + ECHO_SERVER_TIMEOUT
            pid_file = '/run/zephyr_echo_server.' + str(port) + '.pid'
            while self.cli.exists(pid_file):
                time.sleep(1)
                if time.time() > timeout:
                    terminate_process(proc.process, signal='KILL')
                    break
            self.cli.rm(pid_file)
            self.echo_server_procs[port] = None

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=DEFAULT_ECHO_PORT,
                          echo_request='ping', source_ip=None,
                          protocol='tcp'):
        """
        Create a TCP connection to send specified request string to dest_ip
        on dest_port (defaults to localhost:80) and return the response.
        :param dest_ip: str
        :param dest_port: int
        :param echo_request: str
        :param source_ip: str
        :param protocol: str
        :return: str
        """
        self.LOG.debug('Sending echo command ' + echo_request + ' to: ' +
                       str(dest_ip) + ' ' + str(dest_port))
        echo_request += TERMINATION_STRING
        cmd0 = ['echo', '-n', echo_request]
        cmd1 = ['nc']
        if protocol == 'udp':
            cmd1 += ['-u']
        if source_ip:
            cmd1 += ['-s', source_ip]
        cmd1 += ['-w', '20']
        cmd1 += [dest_ip, str(dest_port)]
        ret = self.cli.cmd_pipe(commands=[cmd0, cmd1])
        out_str = ret.stdout
        pos = out_str.find(TERMINATION_STRING)
        if pos != -1:
            out_str = out_str[0:pos]
        self.LOG.debug('Received echo response: ' + out_str)
        return out_str

    @staticmethod
    def is_virtual_network_host():
        """
        Returns True if this Host is running a virtual networking host
        manager (such as midolman), False otherwise
        :return:
        """
        return False

    # Specialized host-testing methods
    def send_custom_packet(self, iface, **kwargs):
        """
        Send a custom TCP packet from this host using args for
        TCPSender::send_packet()
        :type iface: str
        :type kwargs: dict[str, any]
        :return:
        """
        tcps = TCPSender()
        return tcps.send_packet(self.cli, interface=iface, **kwargs).stdout

    def send_arp_packet(self, iface, dest_ip, source_ip=None,
                        command='request',
                        source_mac=None, dest_mac=None,
                        packet_options=None, count=1):
        """
        Send [count] ARP packet(s) from this host with command as "request"
        or "reply".
        :type iface :str
        :type dest_ip: str
        :type source_ip: str
        :type command: str
        :type source_mac: str
        :type dest_mac: str
        :type packet_options: dict[str, str]
        :type count: int
        :return:
        """
        tcps = TCPSender()
        opt_map = {'command': command}
        if source_mac is not None:
            opt_map = {'smac': source_mac}
        if dest_mac is not None:
            opt_map = {'tmac': dest_mac}
        if source_ip is not None:
            opt_map = {'sip': source_ip}
        if dest_ip is not None:
            opt_map = {'tip': dest_ip}
        opt_map += packet_options
        return tcps.send_packet(self.cli, interface=iface, dest_ip=dest_ip,
                                packet_type='arp',
                                packet_options=opt_map, count=count).stdout

    def send_tcp_packet(self, iface, dest_ip,
                        source_port, dest_port, data=None,
                        packet_options=None, count=1):
        """
        Send [count] TCP packets from this Host using TCPSender::Send_packet()
        :type iface: str
        :type dest_ip: str
        :type source_port: int
        :type dest_port: int
        :type data: str
        :type packet_options: dict[str,str]
        :type count: int
        :return:
        """
        tcps = TCPSender()
        return tcps.send_packet(self.cli,
                                interface=iface,
                                dest_ip=dest_ip,
                                packet_type='tcp',
                                source_port=source_port,
                                dest_port=dest_port,
                                payload=data,
                                packet_options=packet_options,
                                count=count).stdout

    def ping(self, target_ip, iface=None, count=1, timeout=None):
        """
        Ping a target IP.  Can specify the interface to use and/or the number
        of pings to send.  Returns true if all pings succeeded, false
        otherwise.
        :param target_ip: str: target IP in CIDR format
        :param iface: str: Interface or IP to act as source
        :param count: int: Number of pings to send
        :param timeout: int: Timeout before packets is marked as failed
        :return: bool
        """
        iface_str = (('-I ' + iface) if iface is not None else '')
        timeout_str = (('-W ' + str(timeout) + ' ')
                       if timeout is not None
                       else '')
        return self.cli.cmd('ping -n ' + iface_str +
                            ' -c ' + str(count) + ' ' +
                            timeout_str +
                            target_ip).ret_code == 0

    def start_capture(self, interface, count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None, save_dump_file=False,
                      save_dump_filename=None):
        """
        Starts the capture of packets on the host's interface with
        pcap_filter tools (e.g. tcpdump). This will start a process
        in the background listening for packets on the given interface.
        The actual packets can be retrieved via the 'capture_packets'
        method.  Capturing can be halted with the 'stop_capture'
        method.  Only one capture can be running per interface at any
        one time.  Use the PcapRule objects to assemble a filter via
        standard pcap_filter rules. A callback function is available
        to be called when each packet is parsed.  It must take at least
        a single PCAPPacket parameter, and any number of optional
        arguments (passed through the callback_args parameter).  The
        packet capture will be dumped to a temporary file, which can
        be saved off to a permanent location, if desired.
        :param interface: str: Interface to capture on ('any' is
        also acceptable)
        :param count: int: Number of packets to capture, or '0' to
        capture until explicitly stopped (default)
        :param ptype: str: Type of packet to filter
        :param pfilter: PcapRule: Ruleset for packet filtering
        :param callback: callable: Optional callback function
        :param callback_args: list[T]: Arguments to optional callback
        function
        :param save_dump_file: bool: Optionally save the temporary
        packet capture file
        :param save_dump_filename: str: Filename to save temporary
        packet capture file
        :return:
        """
        tcpd = (self.packet_captures[interface]
                if interface in self.packet_captures
                else TCPDump())
        """ :type: TCPDump """

        self.LOG.debug('Starting tcpdump on host: ' + self.name)

        old_log = self.cli.log_cmd
        if self.debug:
            self.cli.log_cmd = True

        tcpd.start_capture(cli=self.cli, interface=interface, count=count,
                           packet_type=ptype, pcap_filter=pfilter,
                           callback=callback, callback_args=callback_args,
                           save_dump_file=save_dump_file,
                           save_dump_filename=save_dump_filename,
                           blocking=False)

        self.cli.log_cmd = old_log

        self.packet_captures[interface] = tcpd

    def capture_packets(self, interface, count=1, timeout=None):
        """
        Wait for and return a list of [count] received packets on the given
        interface. The optional timeout can be specified to bound the time
        waiting for the packets (an exception will be raised if the timeout
        is hit).
        :param interface: str: Interface on which to wait for packets
        :param count: int: Number of packets to wait for (0 means just
        return what is buffered)
        :param timeout: int: Upper bound on length of time to wait before
        exception is raised
        :return: list [PCAPPacket]
        """
        if interface not in self.packet_captures:
            raise ObjectNotFoundException(
                'No packet capture is running or was run on host/interface' +
                self.name + '/' + interface)
        tcpd = self.packet_captures[interface]
        return tcpd.wait_for_packets(count, timeout)

    def stop_capture(self, interface):
        """
        Stop the capture of packets on the given interface.  Any
        remaining packets can be accessed through the 'capture_packets'
        method.
        :param interface: str: Interface to stop capture on
        :return:
        """
        if interface in self.packet_captures:
            tcpd = self.packet_captures[interface]
            tcpd.stop_capture()

    def flush_arp(self):
        """
        Flush the ARP table on this Host
        :return:
        """
        self.cli.cmd('ip neighbour flush all')
