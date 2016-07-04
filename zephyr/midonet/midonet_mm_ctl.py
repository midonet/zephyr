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

import time

from zephyr.common import exceptions
from zephyr.midonet import mn_api_utils


def bind_port(mn_api_url, host_id, port_id, interface_name):
    mn_api = mn_api_utils.create_midonet_client(mn_api_url)

    hosts = mn_api.get_hosts(query={})
    bind_host = next(h
                     for h in hosts
                     if h.get_id() == str(host_id))

    (bind_host.add_host_interface_port()
     .port_id(port_id)
     .interface_name(interface_name).create())

    deadline = time.time() + 10

    new_port = mn_api.get_port(port_id)
    while not new_port.get_active():
        if time.time() > deadline:
            raise exceptions.SubprocessTimeoutException(
                "Port binding did not finish within 10 seconds")
        time.sleep(0)
        new_port = mn_api.get_port(port_id)


def unbind_port(mn_api_url, host_id, port_id):
    mn_api = mn_api_utils.create_midonet_client(mn_api_url)
    hosts = mn_api.get_hosts(query={})
    bind_host = next(h
                     for h in hosts
                     if h.get_id() == str(host_id))
    for port in bind_host.get_ports():
        if port.get_port_id() == port_id:
            port.delete()
            return
    raise exceptions.ObjectNotFoundException(
        'Port not found: ' + str(port_id))
