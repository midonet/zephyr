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
import datetime

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
            if self.logger is None:
                print '>>> ' + cmd
            else:
                self.logger.debug('>>>' + cmd)

        if self.debug is True:
            return cmd
        if self.env_map is not None:
            if self.logger is None:
                print "ENV:" + ','.join([k + '=' + self.env_map[k] for k in self.env_map.iterkeys()])
            else:
                self.logger.debug("ENV:" + ','.join([k + '=' + self.env_map[k] for k in self.env_map.iterkeys()]))

        p = subprocess.Popen(cmd, *args, shell=shell, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, env=self.env_map)
        self.last_process = p
        if blocking is False:
            return p

        out = ''
        for line in p.stdout:
            out += line

        # 'timeout' returns 124 on timeout
        if p.returncode == 124 and timeout is not None:
            raise SubprocessTimeoutException('Process timed out: ' + cmd)

        if return_status is True:
            p.poll()
            return p.returncode

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
        return self.cmd('cp ' + old_file + ' ' + new_file)

    @staticmethod
    def read_from_file(file_name):
        file_ptr = open(file_name, 'r')
        return file_ptr.read()

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

    def rollover_file_by_date(self, filename, dest_dir=None,
                              date_pattern='%Y%m%d%H%M%S', zip_file=True):
        """
        If the filename exists, roll it over to a new file based on the parameters.  Return
        the name of the new file.
        :type filename: str
        :type dest_dir: str
        :type date_pattern: str
        :type zip_file: bool
        :return: str
        """
        if self.exists(filename):
            suff_str = '.' + datetime.datetime.now().strftime(date_pattern)

            if dest_dir is not None:
                dest_filename = dest_dir + '/' + os.path.basename(filename) + suff_str
                if not self.exists(dest_dir):
                    self.mkdir(dest_dir)
            else:
                dest_filename = filename + suff_str

            self.copy_file(filename, dest_filename)
            self.rm(filename)

            if zip_file:
                self.cmd('gzip -9 ' + dest_filename)
                dest_filename += '.gz'

            return dest_filename

        return filename


class NetNSCLI(LinuxCLI):
    def __init__(self, name, priv=True, debug=DEBUG, print_cmd=DEBUG):
        super(NetNSCLI, self).__init__(priv, debug)
        self.name = name

    def create_cmd(self, cmd_line):
        return super(NetNSCLI, self).create_cmd('ip netns exec ' + self.name + ' ' + cmd_line)

    def create_cmd_priv(self, cmd_line):
        return super(NetNSCLI, self).create_cmd_priv('ip netns exec ' + self.name + ' ' + cmd_line)

