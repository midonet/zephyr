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

from PTM.impl.PhysicalTopologyManagerImpl import PhysicalTopologyManagerImpl
from PTM.ptm_constants import PTM_LOG_FILE_NAME


class PreconfiguredHostPTMImpl(PhysicalTopologyManagerImpl):
    """
    Assumes a host-based physical topology which has been preconfigured
    by the user, and should not be started/torn-down, only connected to
    for various host-based operations.
    """
    def __init__(self, root_dir='.', log_manager=None, log=None, console=None, log_level=logging.INFO):
        super(PreconfiguredHostPTMImpl, self).__init__(root_dir, log_manager, log, console, log_level)

    def configure_logging(self, log_name='ptm-root', debug=False, log_file_name=PTM_LOG_FILE_NAME):
        super(PreconfiguredHostPTMImpl, self).configure_logging(log_name, debug, log_file_name)

    def configure(self, config_file, file_type='json'):
        pass

    def startup(self):
        pass

    def shutdown(self):
        pass

    def ptm_host_app_control(self, app_cmd, host_json, app_json, arg_list):
        pass

    def create_vm(self, ip, gw_ip=None, requested_hv_host=None, requested_vm_name=None):
        pass
