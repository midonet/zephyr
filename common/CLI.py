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

import os
import subprocess
import logging
import pwd
import glob

from common.Exceptions import *

CREATENSCMD = lambda name: LinuxCLI().cmd('ip netns add ' + name)
REMOVENSCMD = lambda name: LinuxCLI().cmd('ip netns del ' + name)
DEBUG = 0

class CommandStatus(object):
    def __init__(self, process=None, command='', ret_code=0, stdout='', stderr='', process_array=None):
        """
        :type process: subprocess.Popen
        :type ret_code: int
        :type cmd: str
        :type stdout: str
        :type stderr: str
        :type process_array
        :return:
        """
        self.process = process
        self.ret_code = ret_code
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.process_array = process_array

    def __repr__(self):
        return 'PID: ' + str(self.process.pid) + '\n' + \
               'RETCODE: ' + str(self.ret_code) + '\n' + \
               'CMD: ' + self.command + '\n' + \
               'STDOUT: [' + self.stdout + ']' + '\n' + \
               'STDERR: [' + self.stderr + ']'


class LinuxCLI(object):
    def __init__(self, priv=True, debug=(DEBUG >= 2), log_cmd=(DEBUG >= 1), print_cmd_out=(DEBUG >= 1), logger=None):
        self.env_map = None
        """ :type: dict[str, str]"""
        self.priv = priv
        """ :type: bool"""
        self.debug = debug
        """ :type: bool"""
        self.log_cmd = log_cmd
        """ :type: bool"""
        self.logger = logger
        """ :type: logging.Logger"""
        self.print_cmd_out = print_cmd_out
        """ :type: bool"""

    def add_environment_variable(self, name, val):
        if (self.env_map is None):
            self.env_map = {}
        self.env_map[name] = val

    def remove_environment_variable(self, name):
        if (self.env_map is not None):
            self.env_map.pop(name)

    def cmd_pipe(self, commands, timeout=None, blocking=True, verify=False,
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        """
        Execute piped commands on the system without a shell.  The exact command will be
        transformed based on the timeout parameter and whether or not the command is being
        run against an IP net namespace.  The parameter is a list of commands to pipe together,
        with each item being the [base command to run + args] as a list.
        :type commands: list[list[str]]
        :type timeout: int
        :type blocking: bool
        :param stdin: int File descriptor for std in (PIPE by default)
        :param stdout: int File descriptor for std in (PIPE by default)
        :param stderr: int File descriptor for std in (PIPE by default)
        :return CommandStatus:
        """
        ret = CommandStatus()
        if len(commands) == 0:
            return ret

        cmd_array = [(['timeout'] if timeout else []) +
                     self.priv_prefix().split() + self.cmd_prefix().split() + commands[0]]

        for cmd in commands[1:]:
            cmd_array.append(self.priv_prefix().split() + self.cmd_prefix().split() + cmd)

        if self.log_cmd is True:
            if self.logger is not None:
                self.logger.debug('>>>' + str(cmd_array))
            else:
                print('>>>' + str(cmd_array))

        cmd_str = '|'.join([' '.join(i) for i in cmd_array])
        if self.debug is True:
            return CommandStatus(command=cmd_str)

        processes = []
        """ :type: list[subprocess.Popen]"""

        # First process, should have user-set stdin
        # Second -> Second to last (if more than one), chain the stdout -> next stdin
        # The last process (whether one or many) needs to have the user-set stdout, stderr
        for i in range(0, len(cmd_array)):
            p = subprocess.Popen(cmd_array[i], shell=False,
                                 stdin=stdin if i == 0 else processes[i-1].stdout,
                                 stdout=stdout if i == len(cmd_array)-1 else subprocess.PIPE,
                                 stderr=stderr if i == len(cmd_array)-1 else subprocess.PIPE,
                                 env=self.env_map,
                                 preexec_fn=os.setsid)
            processes.append(p)

        # The resulting process error code, output, etc is dependent on last process
        # to run in pipe-chain
        p = processes[-1]

        if blocking is False:
            return CommandStatus(process=p, command=cmd_str, process_array=processes)

        stdout, stderr = p.communicate()

        # 'timeout' returns 124 on timeout
        if p.returncode == 124 and timeout is not None:
            raise SubprocessTimeoutException('Process timed out: ' + cmd_str)

        out = ''
        for line in stdout:
            out += line

        err = ''
        for line in stderr:
            err += line

        if verify and p.returncode != 0:
            raise SubprocessFailedException('Command: [' + str(cmd) + '] returned error: ' +
                                            str(p.returncode) + ', output was stdout[' +
                                            str(out) + ']/stderr[' + str(err) + ']')

        if self.print_cmd_out:
            print "stdout: " + str(out) + "/stderr: " + str(err)

        return CommandStatus(process=p, command=cmd_str, ret_code=p.returncode,
                             stdout=out, stderr=err, process_array=processes)

    def cmd(self, cmd_line, timeout=None, blocking=True, verify=False,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        """
        Execute a shell command on the system.  The exact command will be transformed based
         on the timeout parameter and whether or not the command is being run against
         an IP net namespace.
        :param cmd_line: str The base command to run
        :param timeout: int Timeout value, None for no timeout
        :param blocking: bool Block on this command or return the running process.
        :param stdin: int File descriptor for std in (PIPE by default)
        :param stdout: int File descriptor for std in (PIPE by default)
        :param stderr: int File descriptor for std in (PIPE by default)
        :return CommandStatus:
        """
        cmd = ('timeout ' + str(timeout) + ' ' if timeout is not None else '') + \
              self.priv_prefix() + self.cmd_prefix() + cmd_line

        if self.log_cmd is True:
            if self.logger is not None:
                self.logger.debug('>>>' + cmd)
            else:
                print('>>>' + cmd)

        if self.debug is True:
            return CommandStatus(command=cmd)

        p = subprocess.Popen(cmd, shell=True,
                             stdin=stdin, stdout=stdout, stderr=stderr,
                             env=self.env_map, preexec_fn=os.setsid)
        if blocking is False:
            return CommandStatus(process=p, command=cmd)

        o, e = p.communicate()

        # 'timeout' returns 124 on timeout
        if p.returncode == 124 and timeout is not None:
            raise SubprocessTimeoutException('Process timed out: ' + cmd)

        out = ''
        for line in o if o else []:
            out += line

        err = ''
        for line in e if e else []:
            err += line

        if verify and p.returncode != 0:
            raise SubprocessFailedException('Command: [' + str(cmd) + '] returned error: ' +
                                            str(p.returncode) + ', output was stdout[' +
                                            str(out) + ']/stderr[' + str(err) + ']')

        if self.print_cmd_out:
            print "stdout: " + str(out) + "/stderr: " + str(err)

        return CommandStatus(process=p, command=cmd, ret_code=p.returncode, stdout=out, stderr=err)

    def cmd_prefix(self):
        return ''

    def priv_prefix(self):
        return 'sudo -E ' if self.priv else ''

    def oscmd(self, *args, **kwargs):
        return LinuxCLI().cmd(*args, **kwargs).stdout

    def grep_file(self, gfile, grep, options=''):
        if self.cmd('grep -q ' + options + ' "' + grep + '" ' + gfile).ret_code == 0:
            return True
        else:
            return False

    def grep_cmd(self, cmd_line, grep, options=''):
        if self.cmd(cmd_line + '| grep -q ' + options + ' "' + grep + '"').ret_code == 0:
            return True
        else:
            return False

    def mkdir(self, dir_name):
        return self.cmd('mkdir -p ' + dir_name).stdout

    def chown(self, file_name, user_name, group_name):
        return self.cmd('chown -R ' + user_name + '.' + group_name + ' ' + file_name).stdout

    def regex_file(self, rfile, regex):
        return self.cmd('sed -e "' + regex + '" -i ' + rfile).stdout

    def regex_file_multi(self, rfile, *args):
        sed_str = ''.join(['-e "' + str(i) + '" ' for i in args])
        return self.cmd('sed ' + sed_str + ' -i ' + rfile).stdout

    def get_running_pids(self):
        """
        Gets all running processes' PIDS as a list
        :return: list[str]
        """
        return [i.strip() for i in self.cmd("ps -aef | grep -v grep | awk '{print $2}'").stdout.split()]

    def get_process_pids(self, process_name):
        """
        Gets all running processes' PIDS which match the process name as a list
        :return: list[str]
        """
        awk_cmd = r'{printf "%s\n", $2}'
        return [i.strip() for i in
                self.cmd("ps -aef | grep -v grep | grep " + process_name + r" | awk '" + awk_cmd + r"'").stdout.split()]

    def get_parent_pids(self, child_pid):
        """
        Gets all running processes' PIDS which match the process name as a list
        :return: list[str]
        """
        return [i.strip() for i in
                self.cmd("ps -aef | grep -v grep | awk '{ if ($3==" + str(child_pid) + ") print $2 }'").stdout.split()]

    def is_pid_running(self, pid):
        return str(pid) in self.get_running_pids()

    def replace_text_in_file(self, rfile, search_str, replace_str, line_global_replace=False):
        """
        Replace text line-by-line in given file, on each line replaces all or only first
        occurrence on each line, depending on the global replace flag.
        :type rfile: str
        :type search_str: str
        :type replace_str: str
        :type line_global_replace: bool
        """
        global_flag = 'g' if line_global_replace is True else ''
        # Escape control characters
        new_search_str = search_str
        new_replace_str = replace_str
        search_chars = "\\/\"`[]*+.^!$"
        for c in search_chars:
            if c in new_search_str:
                new_search_str = new_search_str.replace(c, "\\" + c)
        replace_chars = "\\/\"`"
        for c in replace_chars:
            if c in new_replace_str:
                new_replace_str = new_replace_str.replace(c, "\\" + c)

        sed_str = "sed -e 's/" + new_search_str + "/" + new_replace_str + "/" + global_flag + "' -i " + rfile
        return self.cmd(sed_str).stdout

    def copy_dir(self, old_dir, new_dir):
        return self.cmd('cp -RL --preserve=all ' + old_dir + ' ' + new_dir).stdout

    def copy_file(self, old_file, new_file):
        dir = os.path.dirname(new_file)
        if dir != '' and dir != '.' and not self.exists(dir):
            self.mkdir(dir)
        return self.cmd('cp ' + old_file + ' ' + new_file).stdout

    def move(self, old_file, new_file):
        self.copy_dir(old_file, new_file)
        self.rm(old_file)

    @staticmethod
    def read_from_file(file_name):
        file_ptr = open(file_name, 'r')
        return file_ptr.read()

    @staticmethod
    def ls(file_filter='./*'):
        file_list = [f
                     for f in glob.glob(file_filter)
                     if os.path.isfile(f)]
        return file_list

    def wc(self, file):
        if not self.exists(file):
            raise ObjectNotFoundException('File not found: ' + file)
        line = map(int, self.cmd("wc " + file).stdout.split()[0:3])
        return dict(zip(['lines', 'words', 'chars'], line))

    def write_to_file(self, wfile, data, append=False):
        old_data = ''
        if append is True:
            with open(wfile, 'r') as f:
                old_data = f.read()

        self.rm("./.tmp.file")
        file_ptr = open("./.tmp.file", 'w')
        file_ptr.write(old_data + data)
        file_ptr.close()
        ret = self.copy_file('./.tmp.file', wfile)
        self.rm("./.tmp.file")
        if self.debug:
            print 'Would have written: ' + data

        return ret

    def rm(self, old_file):
        forbidden_rms = ['/', '.', '/usr', '/usr/local', '/bin', '/root', '/etc', '/usr/bin', '/usr/local/bin',
                         '/var', '/var/lib', '/home', '/lib', '/usr/lib', '/usr/local/lib', '/boot']

        if old_file in forbidden_rms:
            raise ArgMismatchException('Not allowed to remove ' + old_file +
                                       ' as it is listed as a vital system directory')
        return self.cmd('rm -rf ' + old_file).stdout

    def rm_files(self, root_dir, match_pattern=''):
        if match_pattern == '':
            return self.cmd('find ' + root_dir + ' -type f -exec sudo rm -f {} \; || true').stdout
        else:
            return self.cmd('find ' + root_dir + ' -name ' + match_pattern + ' -exec sudo rm -f {} \; || true').stdout

    @staticmethod
    def exists(efile):
        return os.path.exists(efile)

    def mount(self, drive, as_drive):
        return self.cmd('mount --bind ' + drive + ' ' + as_drive).stdout

    def unmount(self, drive):
        return self.cmd('umount -l ' + drive + " > /dev/null 2>&1").stdout

    def start_screen(self, host, window_name, cmd_line):
        cmd_in_screen = self.priv_prefix() + self.cmd_prefix() + cmd_line
        if self.grep_cmd('screen -ls', host) is False:
            # first screen = main screen
            cmd_opts = '-d -m -S ' + host
        else:
            # subsequent screens = sub screens
            cmd_opts = '-S ' + host + ' -X screen'
        return self.cmd('screen ' + cmd_opts + ' -t ' + window_name + ' /bin/bash -c "' + cmd_in_screen + '"').stdout

    def start_screen_unshare(self, host, window_name, cmd_line):
        return self.start_screen(host, window_name, 'unshare -m ' + cmd_line)

    def os_name(self):
        return self.cmd('cat /etc/*-release | grep ^NAME= | cut -d "=" -f 2').stdout.strip('"').lower()

    def pwd(self):
        return self.cmd('pwd').stdout.strip()

    def whoami(self):
        return pwd.getpwuid(os.getuid())[0]

    def add_to_host_file(self, name, ip):
        host_line = self.cmd('grep -w ' + name + ' /etc/hosts').stdout.splitlines(False)
        if len(host_line) == 0:
            self.write_to_file('/etc/hosts', ip + ' ' + name + '\n', append=True)
        else:
            match_num = 0
            for hl in host_line:
                if hl.split()[0] != ip:
                    match_num += 1
                    if match_num > 1:
                        self.regex_file('/etc/hosts', '/{0} {1}/d'.format(hl.split()[0], name))
                    else:
                        self.regex_file('/etc/hosts', 's/{0} {2}/{1} {2}/g'.format(hl.split()[0], ip, name))


class NetNSCLI(LinuxCLI):
    def __init__(self, name, priv=True, debug=(DEBUG >= 2), log_cmd=(DEBUG >= 2), logger=None):
        super(NetNSCLI, self).__init__(priv, debug=debug, log_cmd=log_cmd, logger=logger)
        self.name = name

    def cmd_prefix(self):
        return 'ip netns exec ' + self.name + ' '
