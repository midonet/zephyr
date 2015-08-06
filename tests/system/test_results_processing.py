__author__ = 'micucci'
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

from common.Exceptions import *

from TSM.TestCase import TestCase

from tests.scenarios.AllInOne import AllInOneScenario
from AllInOneCopy import AllInOneCopyScenario

import unittest


class TestResultsProcessing(TestCase):
    api = None
    """ :type: MidonetApi """
    main_bridge = None
    """ :type: Bridge"""

    @staticmethod
    def supported_scenarios():
        return {AllInOneScenario, AllInOneCopyScenario}

    def test_passed_test(self):
        pass

    def test_failed_test(self):
        self.assertTrue(False)

    def test_error_test(self):
        raise TestException('test')

    @unittest.skip('testing skip')
    def test_skipped_test(self):
        pass

    @unittest.expectedFailure
    def test_expected_failure_test(self):
        self.assertTrue(False)

    @unittest.expectedFailure
    def test_unexpected_pass_test(self):
        pass
