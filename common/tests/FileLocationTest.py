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

import unittest
from common.FileLocation import *
from common.CLI import LinuxCLI


class FileLocationTest(unittest.TestCase):
    def test_get_file(self):
        try:
            cli = LinuxCLI(priv=False)
            cli.write_to_file('test', 'teststr')
            cli.write_to_file('testdir/test2', 'test2str')
            fl = FileLocation('test')
            self.assertEqual('.', fl.path)
            fl.get_file(FileAccessor(), near_filename='test_copy')
            self.assertTrue(cli.exists('test_copy'))

            fl2 = FileLocation('testdir/test2')
            self.assertEqual('testdir', fl2.path)

            #fl2.get_file(SSHFileAccessor('localhost', LinuxCLI().whoami()), near_filename='test2_copy')
            #self.assertTrue(cli.exists('test2_copy'))

        finally:
            LinuxCLI().rm('test')
            LinuxCLI().rm('testdir')
            LinuxCLI().rm('test_copy')
            LinuxCLI().rm('test2_copy')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(FileLocationTest)
