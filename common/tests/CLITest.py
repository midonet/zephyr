__author__ = 'micucci'

import unittest
import os
from common.CLI import *

class CLITest(unittest.TestCase):
    def test_write_file(self):
        LinuxCLI().rm('tmp-test')
        LinuxCLI().write_to_file('tmp-test', 'test1\n')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'), 'test1\n')
        LinuxCLI().write_to_file('tmp-test', 'test2\n', append=True)
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'), 'test1\ntest2\n')
        LinuxCLI(priv=True).write_to_file('tmp-test', 'test3\n', append=True)
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'), 'test1\ntest2\ntest3\n')
        LinuxCLI().rm('tmp-test')

    def test_replace_in_file(self):
        LinuxCLI().write_to_file('tmp-test', 'easy\n"harder"\n#"//[({<hardest>}).*]//"')
        LinuxCLI().replace_text_in_file('tmp-test', 'easy', 'hard')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'), 'hard\n"harder"\n#"//[({<hardest>}).*]//"')
        LinuxCLI().replace_text_in_file('tmp-test', '"harder"', '(not-so-hard)')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'), 'hard\n(not-so-hard)\n#"//[({<hardest>}).*]//"')
        LinuxCLI().replace_text_in_file('tmp-test', '#"//[({<hardest>}).*]//"', '"{[(*pretty*-<darn>-.:!hard!:.)]}"')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'),
                          'hard\n(not-so-hard)\n"{[(*pretty*-<darn>-.:!hard!:.)]}"')

        LinuxCLI().write_to_file('tmp-test',
                                 'global-testglobal-test\nglobal-test\n\nhere globally is a global-test but global')
        LinuxCLI().replace_text_in_file('tmp-test', 'global', 'local')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'),
                          'local-testglobal-test\nlocal-test\n\nhere locally is a global-test but global')
        LinuxCLI().replace_text_in_file('tmp-test', 'global', 'local')
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'),
                          'local-testlocal-test\nlocal-test\n\nhere locally is a local-test but global')

        LinuxCLI().write_to_file('tmp-test',
                                 'global-testglobal-test\nglobal-test\n\nhere globally is a global-test but global')
        LinuxCLI().replace_text_in_file('tmp-test', 'global', 'local', line_global_replace=True)
        self.assertEquals(LinuxCLI().read_from_file('tmp-test'),
                          'local-testlocal-test\nlocal-test\n\nhere locally is a local-test but local')

    def test_wc(self):
        cli = LinuxCLI()
        cli.rm('tmp')
        try:
            cli.write_to_file('tmp', 'foo\nbar\nbaz\nbamf zap\n')
            ret = cli.wc('tmp')
            self.assertEqual(4, ret['lines'])
            self.assertEqual(5, ret['words'])
            self.assertEqual(21, ret['chars'])
        finally:
            cli.rm('tmp')

    def tearDown(self):
        LinuxCLI().rm('tmp-test')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(CLITest)
