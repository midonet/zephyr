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

from PTM.PhysicalTopologyManagerImpl import PhysicalTopologyManagerImpl


class NullOStPhysicalTopologyManagerImpl(PhysicalTopologyManagerImpl):
    """
    Assumes a physical OpenStack topology is already running on the machine and any commands
    should be issued straight through to the core OS.  This implementation, however,
    will issue nova helper commands to create a VM.
    """
    def __init__(self, root_dir='.', log_manager=None):
        super(NullOStPhysicalTopologyManagerImpl, self).__init__(root_dir, log_manager)

    def configure_logging(self, log_name='ptm-root':
        super(NullOStPhysicalTopologyManagerImpl, self).configure_logging(log_name, debug, log_file_name)

    def configure(self, config_file, file_type='json'):
        pass

    def startup(self):
        pass

    def shutdown(self):
        pass
