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

import uuid
from zephyr_ptm.ptm.host.ip_netns_host import IPNetNSHost


class VMHost(IPNetNSHost):
    def __init__(self, name, hypervisor_app, uniqueid=uuid.uuid4()):
        super(VMHost, self).__init__(name, hypervisor_app.host.ptm)
        self.hypervisor_app = hypervisor_app
        self.hypervisor_host = hypervisor_app.host
        self.id = str(uniqueid)

    def wait_for_process_start(self):
        pass

    def wait_for_process_stop(self):
        pass

    def shutdown(self):
        super(VMHost, self).shutdown()
        self.hypervisor_host.remove_taps(self)
        self.hypervisor_app.remove_vm(self)
