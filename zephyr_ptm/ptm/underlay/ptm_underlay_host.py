# Copyright 2016 Midokura SARL
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

from zephyr.common import echo_server
from zephyr.common import exceptions
from zephyr.common import ip
from zephyr.vtm.underlay import underlay_host
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm import ptm_utils


class PTMUnderlayHost(underlay_host.UnderlayHost):
    def __init__(self, name, host_obj,
                 vm_type=False, parent_host=None):
        super(PTMUnderlayHost, self).__init__(name)
        self.underlay_host_obj = host_obj
        """:type: zephyr_ptm.ptm.host.host.Host"""
        self.LOG = self.underlay_host_obj.LOG
        self.vm_type = vm_type
        self.parent_host = parent_host

    def create_vm(self, ip_addr, mac, gw_ip, name):
        if self.vm_type:
            raise exceptions.ArgMismatchException(
                "Error; create_vm operation not valid on a VM host")

        if not self.underlay_host_obj.is_hypervisor():
            raise exceptions.ArgMismatchException(
                "Cannot start VM on a host with no hypervisor application.")

        new_vm = ptm_utils.create_vm(
            hv_host_obj=self.underlay_host_obj,
            ip_addr=ip_addr,
            mac=mac,
            gw_ip=gw_ip,
            name=name,
            log=self.LOG)

        return PTMUnderlayHost(name=new_vm.name, host_obj=new_vm,
                               vm_type=True, parent_host=self)

    def plugin_iface(self, iface, port_id):
        if not self.vm_type:
            raise exceptions.ArgMismatchException(
                "Error; plugin_iface operation only valid on a VM host")

        hv_app_type = application.APPLICATION_TYPE_HYPERVISOR
        hv_host = self.parent_host.underlay_host_obj
        """:type: zephyr_ptm.ptm.host.host.Host"""
        if not hv_host.is_hypervisor():
            raise exceptions.ArgMismatchException(
                "VM's parent host is not a hypervisor!  How did the "
                "VM even get started?")
        hv_app = hv_host.applications_by_type[hv_app_type][0]
        """:type: zephyr_ptm.ptm.application.netns_hv.NetnsHV"""
        return hv_app.plugin_iface_to_network(
            vm_host_name=self.name, iface=iface, port_id=port_id)

    def unplug_iface(self, port_id):
        if not self.vm_type:
            raise exceptions.ArgMismatchException(
                "Error; unplug_iface operation only valid on a VM host")

        hv_app_type = application.APPLICATION_TYPE_HYPERVISOR
        hv_host = self.parent_host.underlay_host_obj
        """:type: zephyr_ptm.ptm.host.host.Host"""
        if not hv_host.is_hypervisor():
            raise exceptions.ArgMismatchException(
                "VM's parent host is not a hypervisor!  How did the "
                "VM even get started?")
        hv_app = hv_host.applications_by_type[hv_app_type][0]
        """:type: zephyr_ptm.ptm.application.netns_hv.NetnsHV"""
        hv_app.disconnect_port(port_id=port_id)

    def create_interface(self, iface, mac=None, ip_list=None,
                         linked_bridge=None, vlans=None):
        if not self.vm_type:
            raise exceptions.ArgMismatchException(
                "Error; create_interface operation only valid on a VM host")
        return self.underlay_host_obj.create_interface(
            iface=iface, mac=mac, ip_list=ip_list,
            linked_bridge=linked_bridge, vlans=vlans)

    def add_ip(self, iface_name, ip_addr):
        return self.underlay_host_obj.interfaces[iface_name].add_ip(
            ip.IP.make_ip(ip_addr))

    def get_ip(self, iface_name):
        iface = self.underlay_host_obj.interfaces[iface_name]
        return iface.ip_list[0] if len(iface.ip_list) > 0 else None

    def reset_default_route(self, ip_addr):
        return self.underlay_host_obj.reset_default_route(ip_addr)

    def reboot(self):
        return self.underlay_host_obj.reboot()

    def fetch_file(self, file_type, **kwargs):
        return self.underlay_host_obj.fetch_resources_from_apps(
            file_type, **kwargs)

    def add_route(self, route_ip='default', gw_ip=None, dev=None):
        return self.underlay_host_obj.add_route(route_ip, gw_ip, dev)

    def del_route(self, route_ip):
        return self.underlay_host_obj.del_route(route_ip)

    def start_echo_server(self, ip_addr='localhost',
                          port=echo_server.DEFAULT_ECHO_PORT,
                          echo_data="echo-reply", protocol='tcp'):
        return self.underlay_host_obj.start_echo_server(
            ip_addr, port, echo_data, protocol)

    def stop_echo_server(self, ip_addr='localhost',
                         port=echo_server.DEFAULT_ECHO_PORT):
        return self.underlay_host_obj.stop_echo_server(ip_addr, port)

    def send_echo_request(self, dest_ip='localhost',
                          dest_port=echo_server.DEFAULT_ECHO_PORT,
                          echo_request='ping', source_ip=None,
                          protocol='tcp'):
        return self.underlay_host_obj.send_echo_request(
            dest_ip, dest_port, echo_request, source_ip, protocol)

    def send_custom_packet(self, iface, **kwargs):
        return self.underlay_host_obj.send_custom_packet(iface, **kwargs)

    def send_arp_packet(self, iface, dest_ip, source_ip=None,
                        command='request',
                        source_mac=None, dest_mac=None,
                        packet_options=None, count=1):
        return self.underlay_host_obj.send_arp_packet(
            iface, dest_ip, source_ip, command, source_mac, dest_mac,
            packet_options, count)

    def send_tcp_packet(self, iface, dest_ip,
                        source_port, dest_port, data=None,
                        packet_options=None, count=1):
        return self.underlay_host_obj.send_tcp_packet(
            iface, dest_ip, source_port, dest_port, data,
            packet_options, count)

    def ping(self, target_ip, iface=None, count=1, timeout=None):
        return self.underlay_host_obj.ping(
            target_ip, iface, count, timeout)

    def start_capture(self, interface, count=0, ptype='', pfilter=None,
                      callback=None, callback_args=None, save_dump_file=False,
                      save_dump_filename=None):
        return self.underlay_host_obj.start_capture(
            interface, count, ptype, pfilter,
            callback, callback_args, save_dump_file, save_dump_filename)

    def capture_packets(self, interface, count=1, timeout=None):
        return self.underlay_host_obj.capture_packets(
            interface, count, timeout)

    def stop_capture(self, interface):
        return self.underlay_host_obj.stop_capture(interface)

    def flush_arp(self):
        return self.underlay_host_obj.flush_arp()

    def execute(self, cmd_line, timeout=None, blocking=True):
        result = self.underlay_host_obj.cli.cmd(
            cmd_line, timeout=timeout, blocking=blocking)
        return result

    def terminate(self):
        """
        Kill this Host.
        :return:
        """
        self.underlay_host_obj.net_down()
        self.underlay_host_obj.shutdown()
        self.underlay_host_obj.remove()
