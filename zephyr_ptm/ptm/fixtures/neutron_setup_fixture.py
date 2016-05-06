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

import logging

from zephyr.common.cli import LinuxCLI
from zephyr.common.file_location import FileLocation
from zephyr.vtm import neutron_api


class NeutronSetupFixture(object):
    def __init__(self, ptm_impl):
        """
        Sets up everything all tests will need to run Neutron.
        :type ptm_impl: ptm.impl.configured_host_ptm_impl.ConfiguredHostPTMImpl
        :type logger: logging.logger
        """
        super(NeutronSetupFixture, self).__init__()
        self.ptm_impl = ptm_impl
        self.LOG = None

    def configure_logging(self, logger):
        self.LOG = logger
        if not self.LOG:
            self.LOG = logging.getLogger("neutron-setup-stdout")
            self.LOG.addHandler(logging.StreamHandler())

    def setup(self):
        self.LOG.debug("Running neutron fixture setup")
        neutron_api.setup_neutron(neutron_api.create_neutron_client(),
                                  log=self.LOG)

        LinuxCLI().cmd('chmod 644 /var/log/neutron/neutron-server.log')
        self.ptm_impl.log_manager.add_external_log_file(
            FileLocation('/var/log/neutron/neutron-server.log'),
            '', '%Y-%m-%d %H:%M:%S.%f')

    def teardown(self):
        """
        Cleans up neutron database and restores it to a zero-state.
        Can be overridden by subclasses to change behavior
        """
        self.LOG.debug("Running neutron fixture teardown")
        LinuxCLI(log_cmd=True).cmd(
            'mysqldump --user=root --password=cat neutron > ' +
            self.ptm_impl.log_manager.root_dir + '/neutron.db.dump')
        neutron_api.clean_neutron(log=self.LOG)
