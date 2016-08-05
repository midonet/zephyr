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

import os
from zephyr.common import cli
from zephyr.midonet import mn_backup as mb
from zephyr.tsm import test_case

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../../..'


class UpgradeTestBase(test_case.TestCase):
    def __init__(self, method_name='runTest'):
        super(UpgradeTestBase, self).__init__(method_name=method_name)

    @staticmethod
    def load_zk_mysql_data(base_name,
                           zkserver, mysql_user, mysql_pass,
                           root_dir='/tmp'):
        backup = mb.MidonetBackup(name=base_name, root_dir=root_dir,
                                  zk_server=zkserver,
                                  mysql_user=mysql_user, mysql_pass=mysql_pass)
        backup.load()

    def upgrade_test_main_flow(self, underlay_module, new_version,
                               zkserver, midonet_api_port, midonet_password):
        """
        :type underlay_module:
        tests.midonet.upgrade.upgrade_underlay_base.UpgradeUnderlayBase
        """
        # Do any specific virtual topology preparations
        underlay_module.do_topo_prep()

        # Create any VMs on the ports provided by the specific topo
        underlay_module.start_vms()

        # Do any pre-communications testing
        underlay_module.do_communication_test_pre()

        # Perform pre-upgrade topology checks
        underlay_module.do_topo_verify_pre()

        # Run upgrade preparation
        migrate_pr = underlay_module.migrate_provider_router
        migrate_ert = underlay_module.migrate_extra_routes
        migrate_as = underlay_module.migrate_anti_spoof

        mycli = cli.LinuxCLI()
        mycli.cmd(ROOT_DIR +
                  '/zephyr/midonet/upgrade-script.sh' +
                  ' -v ' + new_version +
                  ' -a ' + midonet_api_port +
                  ' -z ' + zkserver +
                  ' -p ' + midonet_password +
                  (' -P' if migrate_pr else '') +
                  (' -E' if migrate_ert else '') +
                  (' -A' if migrate_as else ''))

        # Restart all applications
        self.vtm.restart_hosts()

        # Perform post-upgrade communications checks
        underlay_module.do_communication_test_post()

        # Perform post-upgrade topology checks
        underlay_module.do_topo_verify_post()

    def rollback(self):
        pass
