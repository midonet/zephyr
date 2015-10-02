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

class LinuxCLI(object):
    def __init__(self, priv=True, debug=(DEBUG >= 2), log_cmd=(DEBUG >= 1), logger=None):
        self.env_map = None
        """ :type: dict[str, str]"""
        self.priv = priv
        """ :type: bool"""
        self.debug = debug
        """ :type: bool"""
        self.log_cmd = log_cmd
        """ :type: bool"""
        self.last_process = None
        """ :type: subprocess.Popen"""
        self.logger = logger
        """ :type: logging.Logger"""

    def add_environment_variable(self, name, val):
        if (self.env_map is None):
            self.env_map = {}
        self.env_map[name] = val

    def remove_environment_variable(self, name):
        if (self.env_map is not None):
            self.env_map.pop(name)

    # TODO: Unify the output of cmd function and make new functions for different types of outputs
    # TODO: Unify the multi and normal cmd functions
    def cmd(self, cmd_line, return_status=False, timeout=None, blocking=True, shell=True, *args):
        """
        Execute a command on the system.  The exact command will be transformed based
         on the timeout parameter and whether or not the command is being run against
         an IP net namespace.
        :param cmd_line: str The base command to run
        :param return_output: bool True to return the output, False to simply execute command
        :param timeout: int Timeout value, None for no timeout
        :param cmd_event: A threading.Event object to set when command is run, or None for no synchronization
        :return:
        """
        new_cmd_line = ('timeout ' + str(timeout) + ' ' if timeout is not None else '') + cmd_line

        if self.priv is True:
            cmd = self.create_cmd_priv(new_cmd_line)
        else:
            cmd = self.create_cmd(new_cmd_line)

        if self.log_cmd is True:
            if self.logger is not None:
                self.logger.debug('>>>' + cmd)
            else:
                print('>>>' + cmd)

        if self.debug is True:
            return cmd


        p = subprocess.Popen(cmd, *args, shell=shell, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, env=self.env_map)
        self.last_process = p
        if blocking is False:
            return p

        stdout, stderr = p.communicate()

        # 'timeout' returns 124 on timeout
        if p.returncode == 124 and timeout is not None:
            raise SubprocessTimeoutException('Process timed out: ' + cmd)

        if return_status is True:
            return p.returncode

        out = ''
        for line in stdout:
            out += line

        return out

    def create_cmd(self, cmd_line):
        return cmd_line

    def create_cmd_priv(self, cmd_line):
        return 'sudo -E ' + cmd_line

    def oscmd(self, *args, **kwargs):
        return LinuxCLI().cmd(*args, **kwargs)

    def grep_file(self, gfile, grep):
        if self.cmd('grep -q "' + grep + '" ' + gfile, return_status=True) == 0:
            return True
        else:
            return False

    def grep_cmd(self, cmd_line, grep):
        if self.cmd(cmd_line + '| grep -q "' + grep + '"', return_status=True) == 0:
            return True
        else:
            return False

    def mkdir(self, dir_name):
        return self.cmd('mkdir -p ' + dir_name)

    def chown(self, file_name, user_name, group_name):
        return self.cmd('chown -R ' + user_name + '.' + group_name + ' ' + file_name)

    def regex_file(self, rfile, regex):
        return self.cmd('sed -e "' + regex + '" -i ' + rfile)

    def regex_file_multi(self, rfile, *args):
        sed_str = ''.join(['-e "' + str(i) + '" ' for i in args])
        return self.cmd('sed ' + sed_str + ' -i ' + rfile)

    def get_running_pids(self):
        """
        Gets all running processes' PIDS as a list
        :return: list[str]
        """
        return [i.strip() for i in self.cmd("ps -aef | grep -v grep | awk '{print $2}'").split()]

    def get_process_pids(self, process_name):
        """
        Gets all running processes' PIDS which match the process name as a list
        :return: list[str]
        """
        awk_cmd = r'{printf "%s\n", $2}'
        return [i.strip() for i in
                self.cmd("ps -aef | grep -v grep | grep " + process_name + r" | awk '" + awk_cmd + r"'").split()]

    def get_parent_pids(self, child_pid):
        """
        Gets all running processes' PIDS which match the process name as a list
        :return: list[str]
        """
        return [i.strip() for i in
                self.cmd("ps -aef | grep -v grep | awk '{ if ($3==" + str(child_pid) + ") print $2 }'").split()]

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
        return self.cmd(sed_str)

    def copy_dir(self, old_dir, new_dir):
        return self.cmd('cp -RL --preserve=all ' + old_dir + ' ' + new_dir)

    def copy_file(self, old_file, new_file):
        dir = os.path.dirname(new_file)
        if dir != '' and dir != '.' and not self.exists(dir):
            self.mkdir(dir)
        return self.cmd('cp ' + old_file + ' ' + new_file)

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
        line = map(int, self.cmd("wc " + file).split()[0:3])
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
        return self.cmd('rm -rf ' + old_file)
    
    def rm_files(self, root_dir, match_pattern=''):
        if match_pattern == '':
            return self.cmd('find ' + root_dir + ' -type f -exec sudo rm -f {} \; || true')
        else:
            return self.cmd('find ' + root_dir + ' -name ' + match_pattern + ' -exec sudo rm -f {} \; || true')

    @staticmethod
    def exists(efile):
        return os.path.exists(efile)

    def mount(self, drive, as_drive):
        return self.cmd('mount --bind ' + drive + ' ' + as_drive)

    def unmount(self, drive):
        return self.cmd('umount -l ' + drive + " > /dev/null 2>&1")

    def start_screen(self, host, window_name, cmd_line):
        cmd_in_screen = self.create_cmd(cmd_line)
        if self.grep_cmd('screen -ls', host) is False:
            # first screen = main screen
            cmd_opts = '-d -m -S ' + host
        else:
            # subsequent screens = sub screens
            cmd_opts = '-S ' + host + ' -X screen'
        return self.cmd('screen ' + cmd_opts + ' -t ' + window_name + ' /bin/bash -c "' + cmd_in_screen + '"')

    def start_screen_unshare(self, host, window_name, cmd_line):
        return self.start_screen(host, window_name, 'unshare -m ' + cmd_line)

    def os_name(self):
        return self.cmd('cat /etc/*-release | grep ^NAME= | cut -d "=" -f 2').strip('"').lower()

    def pwd(self):
        return self.cmd('pwd').strip()

    def whoami(self):
        return pwd.getpwuid(os.getuid())[0]

    def add_to_host_file(self, name, ip):
        host_line = self.cmd('grep -w ' + name + ' /etc/hosts').splitlines(False)
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

    def create_cmd(self, cmd_line):
        return super(NetNSCLI, self).create_cmd('ip netns exec ' + self.name + ' ' + cmd_line)

    def create_cmd_priv(self, cmd_line):
        return super(NetNSCLI, self).create_cmd_priv('ip netns exec ' + self.name + ' ' + cmd_line)

