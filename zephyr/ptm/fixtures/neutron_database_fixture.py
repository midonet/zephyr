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

from zephyr.common.cli import LinuxCLI
from zephyr.common.file_location import FileLocation
from zephyr.ptm.fixtures.service_fixture import ServiceFixture
from zephyr.ptm.physical_topology_manager import PhysicalTopologyManager
from zephyr.vtm.neutron_api import clean_neutron
from zephyr.vtm.neutron_api import setup_neutron


class NeutronDatabaseFixture(ServiceFixture):
    def __init__(self, vtm, ptm, logger):
        """
        Sets up everything all tests will need to run Neutron.
        :type vtm: VirtualTopologyManager
        :type ptm: PhysicalTopologyManager
        :type logger: logging.logger
        """
        super(NeutronDatabaseFixture, self).__init__()
        self.vtm = vtm
        self.ptm = ptm
        self.LOG = logger

        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet = None
        self.main_pub_router = None
        self.api = None

    def setup(self):
        try:
            self.api = self.vtm.get_client()
            """ :type: neutron_client.Client """

            btd = setup_neutron(self.api,
                                log=self.LOG)

            self.main_network = btd.main_net.network
            self.main_subnet = btd.main_net.subnet
            self.pub_network = btd.pub_net.network
            self.pub_subnet = btd.pub_net.subnet
            self.main_pub_router = btd.router.router

            LinuxCLI().cmd('chmod 644 /var/log/neutron/neutron-server.log')
            self.ptm.log_manager.add_external_log_file(
                FileLocation('/var/log/neutron/neutron-server.log'),
                '', '%Y-%m-%d %H:%M:%S.%f')

        except Exception:
            self.teardown()
            raise

    def teardown(self):
        """
        Cleans up neutron database and restores it to a zero-state.
        Can be overridden by subclasses to change behavior
        """
        LinuxCLI(log_cmd=True).cmd(
            'mysqldump --user=root --password=cat neutron > ' +
            self.ptm.log_manager.root_dir + '/neutron.db.dump')
        clean_neutron(log=self.LOG)
