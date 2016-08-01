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

from data_migration import antispoof as asp
from data_migration import midonet_data as md
from data_migration import neutron_data as nd
from data_migration import provider_router as pr
from data_migration import routes as er
from data_migration import zk_util
import logging
from zephyr.common import exceptions
from zephyr.common import zephyr_constants as zc


class DataMigration(object):
    def __init__(self, dry_run=False, debug=False, log_manager=None):

        """
        :type dry_run: bool
        :type debug: bool
        :type log_manager: zephyr.common.log_manager.LogManager
        """
        self.dry_run = dry_run
        self.debug = debug
        if not log_manager:
            self.LOG = logging.getLogger(name="null-data_migration")
            self.LOG.addHandler(logging.NullHandler())
        else:
            self.LOG = log_manager.add_tee_logger(
                file_name=zc.ZEPHYR_LOG_FILE_NAME, name="data_migration",
                file_log_level=logging.DEBUG if self.debug else logging.INFO,
                stdout_log_level=logging.DEBUG if self.debug else logging.INFO)
        self.neutron_data = None
        self.midonet_data = None
        self.data_map = None

    def prepare(self):
        self.neutron_data = nd.prepare()
        self.midonet_data = md.prepare(self.neutron_data)
        self.data_map = {
            "neutron": self.neutron_data,
            "midonet": self.midonet_data
        }

    def migrate(self):
        if not self.data_map:
            raise exceptions.ObjectNotFoundException(
                'No data_map set up.  Run "prepare" first!')
        nd.migrate(self.data_map, dry_run=self.dry_run)
        md.migrate(self.data_map, dry_run=self.dry_run)

    def clean(self):
        zk_util.delete(dry_run=self.dry_run)

    def provider_router_to_edge_router(self, tenant='admin'):
        if not self.data_map:
            raise exceptions.ObjectNotFoundException(
                'No data_map set up.  Run "prepare" first!')
        pr.migrate(self.data_map, tenant, dry_run=self.dry_run)

    def delete_edge_router(self):
        pr.delete_edge_router()

    def midonet_routes_to_extra_routes(self):
        if not self.data_map:
            raise exceptions.ObjectNotFoundException(
                'No data_map set up.  Run "prepare" first!')
        er.migrate(self.data_map, dry_run=self.dry_run)

    def midonet_antispoof_to_allowed_address_pairs(self):
        if not self.data_map:
            raise exceptions.ObjectNotFoundException(
                'No data_map set up.  Run "prepare" first!')
        asp.migrate(self.data_map, dry_run=self.dry_run)
