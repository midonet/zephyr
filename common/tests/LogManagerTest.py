__author__ = 'micucci'
# Copyright 2015 Midokura SARL
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

import unittest
import logging
import os
import datetime

from common.LogManager import LogManager
from common.CLI import LinuxCLI
from common.Exceptions import *
from common.FileLocation import *

class LogManagerTest(unittest.TestCase):
    def test_formats(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))

        try:
            lm.get_format('test_none')
        except ObjectNotFoundException:
            pass
        else:
            self.assertTrue(False, 'Getting wrong format failed to raise ObjectNotFoundException')

        try:
            lm.add_format('test', logging.Formatter('TEST'))
        except ObjectAlreadyAddedException:
            pass
        else:
            self.assertTrue(False, 'Double-adding format failed to raise ObjectAlreadyAddedException')

        self.assertIsNotNone(lm.get_format('test'))

    def test_stdout(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger = lm.add_stdout_logger(format_name='test')
        logger.info("Test!")
        self.assertTrue(True)

    def test_file(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger = lm.add_file_logger('log.txt', format_name='test')
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log.txt', 'r') as f:
            line = f.readlines()
            print 'LOGFILE1\n---------\n' + ''.join(line)
            self.assertEquals(len(line), 2)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)

    def test_levels(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger = lm.add_file_logger('log2.txt', format_name='test', log_level=logging.DEBUG)
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log2.txt', 'r') as f:
            line = f.readlines()
            print 'LOGFILE2\n---------\n' + ''.join(line)
            self.assertEquals(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3") != -1)

    def test_name_generation(self):
        lm = LogManager()
        logger1 = lm.add_file_logger('log.txt')
        logger2 = lm.add_file_logger('log.txt')
        self.assertIsNotNone(lm.get_logger('root0'))
        self.assertIsNotNone(lm.get_logger('root1'))
        logger3 = lm.add_file_logger('log.txt', name='test')
        logger4 = lm.add_file_logger('log.txt')
        self.assertIsNotNone(lm.get_logger('test'))
        self.assertIsNotNone(lm.get_logger('root3'))

    def test_multiple(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger1 = lm.add_file_logger('log3.txt', format_name='test')
        logger2 = lm.add_file_logger('log4.txt', format_name='test', log_level=logging.DEBUG)

        logger1.error("Test1")
        logger1.warning("Test2")
        logger1.debug("Test3")
        logger2.error("Test1b")
        logger2.warning("Test2b")
        logger2.debug("Test3b")

        with open('log3.txt', 'r') as f:
            line = f.readlines()
            print 'LOGFILE3\n---------\n' + ''.join(line)
            self.assertEquals(len(line), 2)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)

        with open('log4.txt', 'r') as f:
            line = f.readlines()
            print 'LOGFILE4\n---------\n' + ''.join(line)
            self.assertEquals(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1b") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2b") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3b") != -1)

    def test_tee(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger = lm.add_tee_logger('log5.txt', name='tee', file_overwrite=True,
                                   file_log_level=logging.DEBUG, stdout_log_level=logging.WARNING,
                                   file_format_name='test', stdout_format_name='test')
        logger.error("Test1")
        logger.warning("Test2")
        logger.debug("Test3")
        with open('log5.txt', 'r') as f:
            line = f.readlines()
            print 'LOGFILE1\n---------\n' + ''.join(line)
            self.assertEquals(len(line), 3)
            self.assertTrue(line[0].find("TEST - ERROR - Test1") != -1)
            self.assertTrue(line[1].find("TEST - WARNING - Test2") != -1)
            self.assertTrue(line[2].find("TEST - DEBUG - Test3") != -1)

    def test_collate(self):
        pass

    def test_rollover(self):

        LinuxCLI().rm('./logs')
        LinuxCLI().rm('./logbak')

        lm = LogManager('./logs')
        lm.set_default_log_level(logging.DEBUG)

        LinuxCLI(priv=False).write_to_file('./logs/test', 'data')
        LinuxCLI(priv=False).write_to_file('./logs/test2', 'data2')

        # Run fresh rollover function before loggers are defined
        lm.rollover_logs_fresh(date_pattern='%Y', zip_file=False)
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertFalse(LinuxCLI().exists('./logs/test'))
            self.assertFalse(LinuxCLI().exists('./logs/test2'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test.' + current_year))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test2.' + current_year))
            self.assertNotEqual(0, os.path.getsize('./logs/log_bak/test.' + current_year))
            self.assertNotEqual(0, os.path.getsize('./logs/log_bak/test2.' + current_year))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1 = lm.add_file_logger(name='main', file_name='test', file_overwrite=True)
        l2 = lm.add_file_logger(name='sub', file_name='test', file_overwrite=False)
        l3 = lm.add_file_logger(name='main2', file_name='test2', file_overwrite=True)

        self.assertIn(FileLocation('./logs/test'), lm.open_log_files)
        self.assertIn(FileLocation('./logs/test2'), lm.open_log_files)
        self.assertEqual(2, len(lm.open_log_files))

        # Running rollover before log files have data should be a no-op,
        # So the empty files should remain
        lm.rollover_logs_by_date()
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test'))
            self.assertTrue(LinuxCLI().exists('./logs/test2'))
            self.assertEqual(0, os.path.getsize('./logs/test'))
            self.assertEqual(0, os.path.getsize('./logs/test2'))
            self.assertFalse(LinuxCLI().exists('./logs/log_bak'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        # Now run a standard rollover with no params, default log dir should be created
        # and regular log files should be moved and zipped
        lm.rollover_logs_by_date()
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test'))
            self.assertTrue(LinuxCLI().exists('./logs/test2'))
            self.assertEqual(0, os.path.getsize('./logs/test'))
            self.assertEqual(0, os.path.getsize('./logs/test2'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        self.assertNotEqual(0, os.path.getsize('./logs/test'))
        self.assertNotEqual(0, os.path.getsize('./logs/test2'))

        # Same as no-params, just with a specified backup dir
        lm.rollover_logs_by_date(backup_dir='./logbak')
        try:
            self.assertTrue(LinuxCLI().exists('./logs/test'))
            self.assertTrue(LinuxCLI().exists('./logs/test2'))
            self.assertEqual(0, os.path.getsize('./logs/test'))
            self.assertEqual(0, os.path.getsize('./logs/test2'))
            self.assertTrue(LinuxCLI().exists('./logbak'))
        finally:
            LinuxCLI().rm('./logbak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        # Now use a specific pattern, making it easy to test for
        # the files' existence
        new_file = lm.rollover_logs_by_date(date_pattern='%Y')
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertTrue(LinuxCLI().exists('./logs/test'))
            self.assertTrue(LinuxCLI().exists('./logs/test2'))
            self.assertEqual(0, os.path.getsize('./logs/test'))
            self.assertEqual(0, os.path.getsize('./logs/test2'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test.' + current_year + '.gz'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test2.' + current_year + '.gz'))
        finally:
            LinuxCLI().rm('./logs/log_bak')

        l1.info('test1')
        l2.info('test2')
        l3.info('test3')

        new_file = lm.rollover_logs_by_date(date_pattern='%Y', zip_file=False)
        try:
            current_year = str(datetime.datetime.now().year)
            self.assertTrue(LinuxCLI().exists('./logs/test'))
            self.assertTrue(LinuxCLI().exists('./logs/test2'))
            self.assertEqual(0, os.path.getsize('./logs/test'))
            self.assertEqual(0, os.path.getsize('./logs/test2'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak'))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test.' + current_year))
            self.assertTrue(LinuxCLI().exists('./logs/log_bak/test2.' + current_year))
        finally:
            LinuxCLI().rm('./logs')

    @classmethod
    def tearDownClass(cls):
        LinuxCLI().rm('log.txt')
        LinuxCLI().rm('log2.txt')
        LinuxCLI().rm('log3.txt')
        LinuxCLI().rm('log4.txt')
        LinuxCLI().rm('log5.txt')

if __name__ == '__main__':
    unittest.main()
