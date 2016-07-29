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

from zephyr.common import ip
from zephyr.common import utils
from zephyr_ptm.ptm.application import application


def create_vm(hv_host_obj, name=None, log=None):
    app_type = application.APPLICATION_TYPE_HYPERVISOR
    hv_app = hv_host_obj.applications_by_type[app_type][0]
    """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV"""

    if not name:
        name = 'vm_ns'

    if log:
        log.debug("Creating VM [" + name + "] on host: " +
                  hv_host_obj.name + ' with name: ' + name)

    new_vm = hv_app.create_vm(name)

    return new_vm


def setup_vm_network(new_vm, ip_addr=None, gw_ip=None, log=None):
    if ip_addr is None:
        new_vm.request_ip_from_dhcp('eth0')
    else:
        new_vm.interfaces['eth0'].add_ip(ip_addr)

    eth0_ip = new_vm.get_ip('eth0')
    new_vm.main_ip = eth0_ip

    if log:
        log.debug("Setting VM [" + new_vm.name + "] IP: " +
                  str(new_vm.main_ip))

    if gw_ip is None:
        gw_ip = utils.make_gateway_ip(ip.IP.make_ip(eth0_ip))

    if log:
        log.debug("Adding default route for VM: " + gw_ip)

    new_vm.add_route(gw_ip=ip.IP.make_ip(gw_ip))

    return new_vm
