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

from zephyr.tsm.test_case import TestCase
from zephyr_ptm.ptm.fixtures import midonet_setup_fixture


class MidonetTestCase(TestCase):

    def __init__(self, method_name='runTest'):
        super(MidonetTestCase, self).__init__(method_name)
        self.midonet_fixture = None
        """:type: MidonetHostSetupFixture"""
        self.api = None
        """ :type: MidonetApi"""

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data
        prior to running the test case function.
        """
        self.midonet_fixture = self.ptm.midonet_setup
        self.api = self.midonet_fixture.api
        super(MidonetTestCase, self).run(result)
