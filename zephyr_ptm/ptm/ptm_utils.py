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
from zephyr_ptm.ptm.application import application


def create_vm(hv_host_obj, ip_addr, mac, gw_ip, name, log=None):
    app_type = application.APPLICATION_TYPE_HYPERVISOR
    hv_app = hv_host_obj.applications_by_type[app_type][0]
    """ :type: zephyr_ptm.ptm.application.netns_hv.NetnsHV"""

    if log:
        log.debug("Creating VM with IP: " + str(ip_addr) +
                  ' on host: ' + hv_host_obj.name + ' with name: ' + name)

    new_vm = hv_app.create_vm(name)

    real_ip = ip.IP.make_ip(ip_addr)
    new_vm.create_interface('eth0', ip_list=[real_ip], mac=mac)
    if gw_ip is None:
        # Figure out a default gw based on IP, usually
        # (IP & subnet_mask + 1)
        subnet_mask = [255, 255, 255, 255]
        if real_ip.subnet != "":
            smask = int(real_ip.subnet)
            subnet_mask = []

            current_mask = smask
            for i in range(0, 4):
                if current_mask > 8:
                    subnet_mask.append(255)
                else:
                    lastmask = 0
                    for j in range(0, current_mask):
                        lastmask += pow(2, 8 - (j + 1))
                    subnet_mask.append(lastmask)
                current_mask -= 8

        split_ip = real_ip.ip.split(".")
        gw_ip_split = []
        for ip_part in split_ip:
            gw_ip_split.append(int(ip_part) &
                               subnet_mask[len(gw_ip_split)])

        gw_ip_split[3] += 1
        gw_ip = '.'.join(map(lambda x: str(x), gw_ip_split))

    if log:
        log.debug("Adding default route for VM: " + gw_ip)

    new_vm.add_route(gw_ip=ip.IP.make_ip(gw_ip))

    return new_vm
