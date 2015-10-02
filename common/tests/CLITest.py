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

    def test_host_file_replacement(self):
        cli = LinuxCLI()
        if cli.exists('/etc/hosts.backup'):
            self.fail("Backup file present, please cleanup to prevent system corruption")
        else:
            cli.copy_file('/etc/hosts', '/etc/hosts.backup')
            try:
                cli.write_to_file('/etc/hosts', '1.1.1.1 foo\n')
                cli.write_to_file('/etc/hosts', '2.2.2.2 bar\n', append=True)
                cli.write_to_file('/etc/hosts', '64.64.64.64 dontchange\n', append=True)
                cli.add_to_host_file('baz', '3.3.3.3')

                self.assertTrue(cli.grep_file('/etc/hosts', '1.1.1.1 foo'))
                self.assertTrue(cli.grep_file('/etc/hosts', '2.2.2.2 bar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '64.64.64.64 dontchange'))
                self.assertTrue(cli.grep_file('/etc/hosts', '3.3.3.3 baz'))

                cli.add_to_host_file('baz', '4.4.4.4')

                self.assertTrue(cli.grep_file('/etc/hosts', '1.1.1.1 foo'))
                self.assertTrue(cli.grep_file('/etc/hosts', '2.2.2.2 bar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz'))

                cli.add_to_host_file('foo', '5.5.5.5')

                self.assertTrue(cli.grep_file('/etc/hosts', '5.5.5.5 foo'))
                self.assertTrue(cli.grep_file('/etc/hosts', '2.2.2.2 bar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz'))

                cli.add_to_host_file('foobar', '6.6.6.6')

                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz'))
                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 foobar'))

                cli.write_to_file('/etc/hosts', '7.7.7.7 bamf blaze\n', append=True)
                cli.add_to_host_file('bamf', '9.9.9.9')

                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 foobar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '9.9.9.9 bamf blaze'))

                cli.write_to_file('/etc/hosts', '#10.10.10.10 test\n', append=True)
                cli.add_to_host_file('test', '11.11.11.11')

                self.assertTrue(cli.grep_file('/etc/hosts', '9.9.9.9 bamf blaze'))
                self.assertTrue(cli.grep_file('/etc/hosts', '11.11.11.11 test'))

                cli.add_to_host_file('baz2', '4.4.4.4')

                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz'))
                self.assertTrue(cli.grep_file('/etc/hosts', '11.11.11.11 test'))
                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz2'))

                cli.add_to_host_file('baz2', '6.6.6.6')

                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 foobar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '4.4.4.4 baz'))
                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 baz2'))

                cli.write_to_file('/etc/hosts', '12.12.12.12 baz\n', append=True)
                cli.add_to_host_file('baz', '13.13.13.13')

                self.assertTrue(cli.grep_file('/etc/hosts', '5.5.5.5 foo'))
                self.assertTrue(cli.grep_file('/etc/hosts', '2.2.2.2 bar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '64.64.64.64 dontchange'))
                self.assertTrue(cli.grep_file('/etc/hosts', '13.13.13.13 baz'))
                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 foobar'))
                self.assertTrue(cli.grep_file('/etc/hosts', '9.9.9.9 bamf blaze'))
                self.assertTrue(cli.grep_file('/etc/hosts', '11.11.11.11 test'))
                self.assertTrue(cli.grep_file('/etc/hosts', '6.6.6.6 baz2'))
                self.assertTrue(cli.grep_file('/etc/hosts', '13.13.13.13 baz'))
                self.assertEqual(1, len(cli.cmd('grep "13.13.13.13 baz" /etc/hosts').splitlines(False)))
                self.assertFalse(cli.grep_file('/etc/hosts', '12.12.12.12 baz'))

            finally:
                cli.copy_file('/etc/hosts', '/tmp/hosts.tested')
                cli.move('/etc/hosts.backup', '/etc/hosts')

    def test_pid_functions(self):
        cli = LinuxCLI()
        root_pids = cli.get_process_pids("root")
        pids = cli.get_running_pids()
        ppids = cli.get_parent_pids("1")

        self.assertTrue(len(root_pids) > 0)
        self.assertTrue(len(pids) > 0)
        self.assertTrue(len(ppids) > 0)

    def tearDown(self):
        LinuxCLI().rm('tmp-test')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(CLITest)
