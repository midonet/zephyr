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

from TSM.TestCase import TestCase
from PTM.fixtures.MidonetHostSetupFixture import MidonetHostSetupFixture


class MidonetTestCase(TestCase):

    def __init__(self, method_name='runTest'):
        super(MidonetTestCase, self).__init__(method_name=method_name)
        self.midonet_fixture = None
        """:type: MidonetHostSetupFixture"""
        self.api = None
        """ :type: MidonetApi"""

    @classmethod
    def _prepare_class(cls, ptm, vtm, test_case_logger=logging.getLogger()):
        """

        :param ptm:
        :type test_case_logger: logging.logger
        """
        super(MidonetTestCase, cls)._prepare_class(ptm, vtm, test_case_logger)

        # Only add the midonet-setup fixture once for each scenario.
        if 'midonet-setup' not in ptm.fixtures:
            test_case_logger.debug('Adding midonet-setup fixture')
            midonet_fixture = MidonetHostSetupFixture(cls.vtm, cls.ptm, test_case_logger)
            ptm.add_fixture('midonet-setup', midonet_fixture)

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data prior to running
        the test case function.
        """
        self.midonet_fixture = self.ptm.get_fixture('midonet-setup')
        self.api = self.midonet_fixture.api
        super(MidonetTestCase, self).run(result)
