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

from common.LogManager import LogManager
from common.CLI import LinuxCLI
from common.Exceptions import *

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

    def test_multiple_same_name(self):
        lm = LogManager()
        lm.add_format('test', logging.Formatter('TEST - %(levelname)s - %(message)s'))
        logger1 = lm.add_file_logger('log.txt', name='test', format_name='test')
        try:
            logger2 = lm.add_file_logger('log.txt', name='test', format_name='test')
        except ObjectAlreadyAddedException:
            pass
        else:
            self.assertTrue(False, 'Double-adding logger failed to raise ObjectAlreadyAddedException')

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
        self.assertEqual(True, False)

    def tearDown(self):
        LinuxCLI().rm('log.txt')
        LinuxCLI().rm('log2.txt')
        LinuxCLI().rm('log3.txt')
        LinuxCLI().rm('log4.txt')
        LinuxCLI().rm('log5.txt')

if __name__ == '__main__':
    unittest.main()
