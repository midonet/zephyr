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

import datetime
import logging
import os
import time
import unittest
from zephyr.common import exceptions
from zephyr.common.file_location import *
from zephyr.common import log_manager
from zephyr.common import log_slicer
from zephyr.common.utils import run_unit_test


class LogSlicerTest(unittest.TestCase):
    def test_slicing_single(self):
        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./sliced-logs')

        try:
            lm = log_manager.LogManager('./logs')
            lm.set_default_log_level(logging.DEBUG)
            log = lm.add_file_logger('test-log')

            now1 = datetime.datetime.now()
            for i in range(0, 5):
                log.info('test-log-line: ' + str(i))
                time.sleep(2)
            log.info('test-log-line: ' + str(5))
            now2 = datetime.datetime.now()

            log_slicer.slice_log_files_by_time(
                log_files=[FileLocation('./logs/test-log')],
                out_dir='./sliced-logs',
                slice_start_time=now1 + datetime.timedelta(seconds=3),
                slice_stop_time=now2 - datetime.timedelta(seconds=3))

            self.assertAlmostEquals(
                2,
                LinuxCLI().wc('./sliced-logs/test-log.slice')['lines'],
                delta=1)

        finally:
            LinuxCLI().rm('./logs')
            LinuxCLI().rm('./sliced-logs')

    def test_slicing_single_leeway(self):
        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./sliced-logs')

        try:
            lm = log_manager.LogManager('./logs')
            lm.set_default_log_level(logging.DEBUG)
            log = lm.add_file_logger('test-log')

            now1 = datetime.datetime.now() + datetime.timedelta(seconds=6)
            for i in range(0, 5):
                log.info('test-log-line: ' + str(i))
                time.sleep(2)
            log.info('test-log-line: ' + str(5))
            now2 = datetime.datetime.now() - datetime.timedelta(seconds=6)

            log_slicer.slice_log_files_by_time(
                log_files=[FileLocation('./logs/test-log')],
                out_dir='./sliced-logs',
                slice_start_time=now1,
                slice_stop_time=now2,
                leeway=3)

            self.assertAlmostEquals(
                2,
                LinuxCLI().wc('./sliced-logs/test-log.slice')['lines'],
                delta=1)

        finally:
            LinuxCLI().rm('./logs')
            LinuxCLI().rm('./sliced-logs')

    def test_slicing_multi(self):
        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./sliced-logs')

        try:
            lm = log_manager.LogManager('./logs')
            lm.set_default_log_level(logging.DEBUG)
            log1 = lm.add_file_logger('test-log')
            log2 = lm.add_file_logger('test-log2')

            now1 = datetime.datetime.now() + datetime.timedelta(seconds=6)
            for i in range(0, 5):
                log1.info('test-log-line: ' + str(i))
                log2.info('test-log2-line: ' + str(i))
                time.sleep(2)
            log1.info('test-log-line: ' + str(5))
            log2.info('test-log2-line: ' + str(5))
            now2 = datetime.datetime.now() - datetime.timedelta(seconds=6)

            log_slicer.slice_log_files_by_time(
                log_files=[FileLocation('./logs/test-log'),
                           FileLocation('./logs/test-log2')],
                out_dir='./sliced-logs',
                slice_start_time=now1,
                slice_stop_time=now2,
                leeway=3)

            self.assertAlmostEquals(
                2,
                LinuxCLI().wc('./sliced-logs/test-log.slice')['lines'],
                delta=1)
            self.assertAlmostEquals(
                2,
                LinuxCLI().wc('./sliced-logs/test-log2.slice')['lines'],
                delta=1)

        finally:
            LinuxCLI().rm('./logs')
            LinuxCLI().rm('./sliced-logs')
            pass

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().rm('log_file.txt')
        LinuxCLI().rm('log_file2.txt')
        LinuxCLI().rm('log_tee.txt')
        LinuxCLI().rm('log_name_generation.txt')
        LinuxCLI().rm('log_levels.txt')
        LinuxCLI().rm('log_multiple.txt')
        LinuxCLI().rm('log_multiple2.txt')
        LinuxCLI().rm('logs')
        LinuxCLI().rm('logs2')
        LinuxCLI().rm('logs3')
        LinuxCLI().rm('logs4')
        LinuxCLI().rm('logs-all')
        LinuxCLI().rm('sliced-logs')

run_unit_test(LogSlicerTest)
