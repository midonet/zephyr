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
import unittest
from zephyr.common.exceptions import ObjectAlreadyAddedException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.common.file_location import *
from zephyr.common.log_manager import LogManager
from zephyr.common.utils import run_unit_test


class LogManagerTest(unittest.TestCase):
    def test_formats(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))

        try:
            lm.get_format('test_none')
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(
                False,
                'Getting wrong format failed to raise '
                'ObjectNotFoundException')

        try:
            lm.add_format('test', logging.Formatter('TEST'))
        except ObjectAlreadyAddedException:
            pass
        else:
            self.assertTrue(
                False,
                'Double-adding format failed to raise '
                'ObjectAlreadyAddedException')

        self.assertIsNotNone(lm.get_format('test'))

    def test_stdout(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))
        logger = lm.add_stdout_logger(format_name='test')
        logger.info("Test!")
        self.assertTrue(True)

    def test_file(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))
        logger = lm.add_file_logger('log_file.txt', format_name='test')
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log_file.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 2)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)

        lm.add_format(
            'test2',
            logging.Formatter(
                fmt='TEST2 - %(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y'),
            '%Y', 1)
        current_year = str(datetime.datetime.now().year)
        logger = lm.add_file_logger('log_file2.txt', format_name='test2')
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log_file2.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 2)
            self.assertTrue(
                line[0].find(
                    "TEST2 - " + str(current_year) +
                    " - ERROR - Test1") != -1)
            self.assertTrue(
                line[1].find(
                    "TEST2 - " + str(current_year) +
                    " - WARNING - Test2") != -1)

    def test_levels(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))
        logger = lm.add_file_logger(
            'log_levels.txt',
            format_name='test',
            log_level=logging.DEBUG)
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log_levels.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3") != -1)

    def test_name_generation(self):
        lm = LogManager()
        lm.add_file_logger('log_name_generation.txt')
        lm.add_file_logger('log_name_generation.txt')
        self.assertIsNotNone(lm.get_logger('root0'))
        self.assertIsNotNone(lm.get_logger('root1'))
        lm.add_file_logger('log_name_generation.txt', name='test')
        lm.add_file_logger('log_name_generation.txt')
        self.assertIsNotNone(lm.get_logger('test'))
        self.assertIsNotNone(lm.get_logger('root3'))

    def test_multiple(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))
        logger1 = lm.add_file_logger(
            'log_multiple.txt',
            format_name='test')
        logger2 = lm.add_file_logger(
            'log_multiple2.txt',
            format_name='test',
            log_level=logging.DEBUG)

        logger1.error("Test1")
        logger1.warning("Test2")
        logger1.debug("Test3")
        logger2.error("Test1b")
        logger2.warning("Test2b")
        logger2.debug("Test3b")

        with open('log_multiple.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 2)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)

        with open('log_multiple2.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1b") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2b") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3b") != -1)

    def test_tee(self):
        lm = LogManager()
        lm.add_format(
            'test',
            logging.Formatter(
                '%(asctime)s TEST - %(levelname)s - %(message)s'))
        logger = lm.add_tee_logger(
            'log_tee.txt',
            name='tee',
            file_overwrite=True,
            file_log_level=logging.DEBUG,
            stdout_log_level=logging.WARNING,
            file_format_name='test',
            stdout_format_name='test')
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log_tee.txt', 'r') as f:
            line = f.readlines()
            self.assertEqual(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3") != -1)

    def test_rollover(self):

        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./logbak')

        lm = LogManager('./logs')
        lm.set_default_log_level(logging.DEBUG)

        LinuxCLI(priv=False).write_to_file('./logs/test.log', 'data')
        LinuxCLI(priv=False).write_to_file('./logs/test2.log', 'data2')

        # Run fresh rollover function before loggers are defined
        lm.rollover_logs_fresh(date_pattern='%Y', zip_file=False)
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertFalse(LinuxCLI().exists('./logs/test.log'))
            self.assertFalse(LinuxCLI().exists('./logs/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists(
                './logs/log_bak/test.log.' + current_year))
            self.assertTrue(LinuxCLI().exists(
                './logs/log_bak/test2.log.' + current_year))
            self.assertNotEqual(0, os.path.getsize(
                './logs/log_bak/test.log.' + current_year))
            self.assertNotEqual(0, os.path.getsize(
                './logs/log_bak/test2.log.' + current_year))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1 = lm.add_file_logger(name='main',
                                file_name='test.log',
                                file_overwrite=True)
        l2 = lm.add_file_logger(name='sub',
                                file_name='test.log',
                                file_overwrite=False)
        l3 = lm.add_file_logger(name='main2',
                                file_name='test2.log',
                                file_overwrite=True)

        self.assertIn(FileLocation('./logs/test.log'), lm.open_log_files)
        self.assertIn(FileLocation('./logs/test2.log'), lm.open_log_files)
        self.assertEqual(2, len(lm.open_log_files))

        # Running rollover before log files have data should be a no-op,
        # So the empty files should remain
        lm.rollover_logs_by_date()
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test.log'))
            self.assertTrue(LinuxCLI().exists('./logs/test2.log'))
            self.assertEqual(0, os.path.getsize('./logs/test.log'))
            self.assertEqual(0, os.path.getsize('./logs/test2.log'))
            self.assertFalse(LinuxCLI().exists('./logs/log_bak'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        # Now run a standard rollover with no params, default log dir should
        # be created and regular log files should be moved and zipped
        lm.rollover_logs_by_date()
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test.log'))
            self.assertTrue(LinuxCLI().exists('./logs/test2.log'))
            self.assertEqual(0, os.path.getsize('./logs/test.log'))
            self.assertEqual(0, os.path.getsize('./logs/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        self.assertNotEqual(0, os.path.getsize('./logs/test.log'))
        self.assertNotEqual(0, os.path.getsize('./logs/test2.log'))

        # Same as no-params, just with a specified backup dir
        lm.rollover_logs_by_date(backup_dir='./logbak')
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test.log'))
            self.assertTrue(LinuxCLI().exists('./logs/test2.log'))
            self.assertEqual(0, os.path.getsize('./logs/test.log'))
            self.assertEqual(0, os.path.getsize('./logs/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logbak'))
        finally:
            LinuxCLI().rm('./logbak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        # Now use a specific pattern, making it easy to test for
        # the files' existence
        lm.rollover_logs_by_date(date_pattern='%Y')
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertTrue(LinuxCLI().exists('./logs/test.log'))
            self.assertTrue(LinuxCLI().exists('./logs/test2.log'))
            self.assertEqual(0, os.path.getsize('./logs/test.log'))
            self.assertEqual(0, os.path.getsize('./logs/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test.log.' +
                                              current_year + '.gz'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test2.log.' +
                                              current_year + '.gz'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        lm.rollover_logs_by_date(date_pattern='%Y', zip_file=False)
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertTrue(LinuxCLI().exists('./logs/test.log'))
            self.assertTrue(LinuxCLI().exists('./logs/test2.log'))
            self.assertEqual(0, os.path.getsize('./logs/test.log'))
            self.assertEqual(0, os.path.getsize('./logs/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test.log.' +
                                              current_year))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test2.log.' +
                                              current_year))
        finally:
            LinuxCLI().rm('./logs')

    def test_collate(self):
        LinuxCLI().rm('./logs-all')
        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./logs2')
        LinuxCLI().rm('./logs3')
        LinuxCLI().rm('./logs4')

        LinuxCLI(priv=False).mkdir('./logs2')
        LinuxCLI(priv=False).mkdir('./logs3')
        LinuxCLI(priv=False).mkdir('./logs4')

        try:
            LinuxCLI(priv=False).write_to_file('./logs2/test2.log', 'data')
            LinuxCLI(priv=False).write_to_file('./logs3/test3.log', 'data2')
            LinuxCLI(priv=False).write_to_file('./logs4/test3.log', 'data3')

            lm = LogManager('./logs')

            lm.set_default_log_level(logging.DEBUG)
            log1 = lm.add_file_logger('test-log.log')
            log2 = lm.add_file_logger('test-log2.log')
            lm.add_external_log_file(FileLocation('./logs2/test2.log'), '')
            lm.add_external_log_file(FileLocation('./logs3/test3.log'), '0')
            lm.add_external_log_file(FileLocation('./logs4/test3.log'), '1')

            log1.info('test')
            log2.info('test2')

            lm.collate_logs('./logs-all')

            self.assertTrue(LinuxCLI().exists('./logs-all/test-log.log'))
            self.assertTrue(LinuxCLI().exists('./logs-all/test-log2.log'))
            self.assertTrue(LinuxCLI().exists('./logs-all/test2.log'))
            self.assertTrue(LinuxCLI().exists('./logs-all/test3.log.0'))
            self.assertTrue(LinuxCLI().exists('./logs-all/test3.log.1'))
        finally:
            LinuxCLI().rm('./logs-all')
            LinuxCLI().rm('./logs')
            LinuxCLI().rm('./logs2')
            LinuxCLI().rm('./logs3')
            LinuxCLI().rm('./logs4')

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

run_unit_test(LogManagerTest)
