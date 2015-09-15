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

from common.CLI import LinuxCLI
import os.path

class FileAccessor(object):
    def __init__(self):
        super(FileAccessor, self).__init__()

    def _get_file(self, far_path, far_filename, near_path, near_filename):
        LinuxCLI(priv=False).copy_file(far_path + '/' + far_filename,
                                       near_path + '/' + near_filename)


class SSHFileAccessor(FileAccessor):
    def __init__(self, remote_server, remote_username):
        super(SSHFileAccessor, self).__init__()
        self.remote_server = remote_server
        self.remote_username = remote_username

    def _get_file(self, far_path, far_filename, near_path, near_filename):
        # For SSH, we must have an absolute path
        if far_path == '.':
            # If path is current dir, expand with PWD
            far_f = LinuxCLI().pwd() + '/' + far_filename
        elif not far_path.startswith('/'):
            # If path is relative to current dir, use PWD as base
            far_f = LinuxCLI().pwd() + '/' + far_path + '/' + far_filename
        else:
            far_f = far_path + '/' + far_filename

        near_f = near_path + '/' + near_filename

        LinuxCLI(log_cmd=True, priv=False).cmd('scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ' +
                                               self.remote_username + '@' + self.remote_server + ':' + far_f + ' ' +
                                               near_f)


class FileLocation(object):
    def __eq__(self, other):
        return self.path == other.path and self.filename == other.filename

    def __hash__(self):
        return hash(self.full_path())

    def __init__(self, filename, default_accessor=FileAccessor()):
        super(FileLocation, self).__init__()
        self.path = os.path.dirname(filename)
        if self.path == '':
            self.path = '.'
        self.filename = os.path.basename(filename)
        self.default_accessor = default_accessor

    def get_file(self, accessor=None, near_path='.', near_filename=None):
        near_fn = near_filename if near_filename is not None else self.filename
        curr_acc = accessor if accessor is not None else self.default_accessor
        curr_acc._get_file(self.path, self.filename, near_path, near_fn)

    def full_path(self):
        return self.path + '/' + self.filename


