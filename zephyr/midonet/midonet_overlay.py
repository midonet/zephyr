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

from zephyr.midonet import midonet_mm_ctl
from zephyr.vtm.underlay import overlay_manager


class MidonetOverlay(overlay_manager.OverlayManager):
    def __init__(self, midonet_api_url=None):
        self.midonet_api_url = midonet_api_url

    def plugin_iface(self, host_id, iface, port_id):
        midonet_mm_ctl.bind_port(
            mn_api_url=self.midonet_api_url,
            host_id=host_id, port_id=port_id,
            interface_name=iface)

    def unplug_iface(self, host_id, port_id):
        midonet_mm_ctl.unbind_port(
            mn_api_url=self.midonet_api_url,
            host_id=host_id, port_id=port_id)
