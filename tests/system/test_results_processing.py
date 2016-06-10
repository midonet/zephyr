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
import time
import unittest

from zephyr.common.exceptions import *
from zephyr.tsm import test_case


class TestResultsProcessing(test_case):
    api = None
    """ :type: MidonetApi """
    main_bridge = None
    """ :type: Bridge"""
    testlog = None
    """ :type: logging.Logger"""

    @classmethod
    def setUpClass(cls):
        cls.testlog = cls.ptm.log_manager.add_file_logger(
            file_name='test-' + cls.__name__ + '.log', name='tester',
            file_overwrite=True, log_level=logging.DEBUG)

    def test_passed_test(self):
        self.testlog.debug('test_passed_test')
        pass

    def test_failed_test(self):
        self.assertTrue(False)

    def test_error_test(self):
        self.LOG.debug('test_error_test')
        raise TestException('test')

    @unittest.skip('testing skip')
    def test_skipped_test(self):
        self.LOG.debug('test_skipped_test')
        pass

    @unittest.expectedFailure
    def test_expected_failure_test(self):
        self.LOG.debug('test_expected_failure_test')
        self.assertTrue(False)

    @unittest.expectedFailure
    def test_unexpected_pass_test(self):
        self.testlog.debug('test_unexpected_pass_test')
        pass

    def test_log_splitting(self):
        self.testlog.debug('test_log_splitting')

        for i in range(0, 10):
            logger = self.ptm.log_manager.get_logger(name='tester')
            logger.info('test_log_splitting')
            self.LOG.info('test_log_splitting_in_main ' + str(i))
            time.sleep(1)

    def test_log_splitting2(self):
        self.testlog.debug('test_log_splitting2')

        for i in range(0, 10):
            self.testlog.info('test_log_splitting2 ' + str(i))
            self.LOG.info('test_log_splitting2_in_main ' + str(i))
            time.sleep(1)
