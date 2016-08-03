#!/usr/bin/env python
#  Copyright 2016 Midokura SARL
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

import getopt
import logging
import sys

from zephyr.common import cli
from zephyr.common import exceptions

DEFAULT_REPO = "http://builds.midonet.org"


class MidonetBackup(object):
    def __init__(self, name, root_dir='/tmp',
                 zkdump=True, mysql=True,
                 zk_server=None,
                 mysql_user='root', mysql_pass=None,
                 debug=False):
        self.name = name
        self.root_dir = root_dir
        self.zkdump = zkdump
        self.mysql = mysql
        self.zk_server = zk_server
        self.mysql_cred = (mysql_user, mysql_pass)
        self.debug = debug
        self.LOG = logging.getLogger(name="midonet_backup")
        self.LOG.setLevel(1)
        file_handler = logging.StreamHandler()
        file_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        self.LOG.addHandler(file_handler)
        self.cli = cli.LinuxCLI(priv=False,
                                log_cmd=self.debug, print_cmd_out=self.debug,
                                logger=self.LOG)

    def save(self):
        if self.zkdump:
            self.LOG.debug('Saving zkdump data')
            cmd_out = self.cli.cmd(
                'zkdump'
                ' -z ' + self.zk_server +
                ' -d' +
                ' -o ' + self.root_dir + '/' + self.name + '.zkdump')
            if cmd_out.ret_code != 0:
                raise exceptions.SubprocessFailedException(
                    "zkdump failed")

        if self.mysql:
            self.LOG.debug('Saving mysql data')
            cmd_out = self.cli.cmd(
                'mysqldump'
                ' -u ' + self.mysql_cred[0] +
                ' --password=' + self.mysql_cred[1] +
                ' neutron' +
                ' > ' + self.root_dir + '/' + self.name + '.mysql')
            if cmd_out.ret_code != 0:
                raise exceptions.SubprocessFailedException(
                    "mysqldump failed")

    def load(self):
        if self.zkdump:
            self.LOG.debug('Loading zkdump data')
            cmd_out = self.cli.cmd(
                'echo "restore" | zkdump'
                ' -z ' + self.zk_server +
                ' -l' +
                ' -i ' + self.root_dir + '/' + self.name + '.zkdump')
            self.LOG.debug(cmd_out.stdout)
            if cmd_out.ret_code != 0:
                raise exceptions.SubprocessFailedException(
                    "zkdump failed")

        if self.mysql:
            self.LOG.debug('Loading mysql data')
            cmd_out = self.cli.cmd(
                'mysql'
                ' -u ' + self.mysql_cred[0] +
                ' --password=' + self.mysql_cred[1] +
                ' -U neutron'
                ' < ' + self.root_dir + '/' + self.name + '.mysql')
            self.LOG.debug(cmd_out.stdout)
            if cmd_out.ret_code != 0:
                raise exceptions.SubprocessFailedException(
                    "mysqldump failed")


def usage():
    print('Usage: mn_backup.py (-s|-l) <dir> -n <name> [-d]')
    print('                    [-z -k <server>] [-m -u <user> -p <pass>]')
    print('')
    print('   Options:')
    print('     -s, --save <dir>')
    print('         Saves dump files to given dir')
    print('     -l, --load <dir>')
    print('         Loads dump files from given dir')
    print('     -n, --name <name>')
    print('         Use name to find files with the .zkdump and .mysql')
    print('         extensions in order to save or load')
    print('     [-z, --zkdump]')
    print('         Save/load zkdump file')
    print('     [-k, --zk-server <server IP:port>]')
    print('         Use the IP:port (no spaces) as the connection string to')
    print('         the zookeeper server')
    print('     [-m, --mysql]')
    print('         Save/load mysql file')
    print('     [-u, --mysql-user <username>]')
    print('         MySQL username to use to dump the database contents')
    print('     [-p, --mysql-pass <password>]')
    print('         MySQL password to use to dump the database contents')
    print('     -d, --debug')
    print('         Turn on debug logging')


if __name__ == "__main__":

    try:
        arg_map, extra_args = getopt.getopt(
            sys.argv[1:],
            (
                'h'
                's:'
                'l:'
                'n:'
                'z'
                'k:'
                'u:'
                'p:'
                'm'
                'd'
            ),
            [
                'help',
                'save=',
                'load=',
                'name=',
                'zkdump',
                'zk-server=',
                'mysql',
                'mysql-user=',
                'mysql-pass=',
                'debug'
            ])

        # Defaults
        command = None
        name = None
        root_dir = None
        zkdump_do = False
        zk_server = None
        mysql_do = False
        mysql_user = None
        mysql_pass = None
        debug = False

        for arg, value in arg_map:
            if arg in ('-h', '--help'):
                usage()
                sys.exit(0)
            elif arg in ('-s', '--save'):
                command = 'save'
                root_dir = value
            elif arg in ('-l', '--load'):
                command = 'load'
                root_dir = value
            elif arg in ('-n', '--name'):
                name = value
            elif arg in ('-r', '--root_dir'):
                root_dir = value
            elif arg in ('-z', '--zkdump'):
                zkdump_do = True
            elif arg in ('-k', '--zk-server'):
                zk_server = value
            elif arg in ('-m', '--mysql'):
                mysql_do = True
            elif arg in ('-u', '--mysql-user'):
                mysql_user = value
            elif arg in ('-p', '--mysql-pass'):
                mysql_pass = value
            elif arg in ('-d', '--debug'):
                debug = True
            else:
                usage()
                raise exceptions.ArgMismatchException('Invalid argument' + arg)

        if not command or not root_dir:
            usage()
            raise exceptions.ArgMismatchException(
                "Must either specify to 'load' or 'save' as well "
                "as a root directory to use")

        if not zkdump_do and not mysql_do:
            usage()
            raise exceptions.ArgMismatchException(
                "Must select to save either mysql or zk data (or both)")

        if zkdump_do and not zk_server:
            usage()
            raise exceptions.ArgMismatchException(
                "Must provide zk server if dumping ZK database")

        if mysql_do and (not mysql_user or not mysql_pass):
            usage()
            raise exceptions.ArgMismatchException(
                "Must provide mysql user and password if dumping mysql "
                "database")

        if not name:
            usage()
            raise exceptions.ArgMismatchException(
                "Must specify a base name to use for the dump files")

        mb = MidonetBackup(name=name, root_dir=root_dir,
                           zkdump=zkdump_do, mysql=mysql_do,
                           mysql_user=mysql_user, mysql_pass=mysql_pass,
                           zk_server=zk_server, debug=debug)

        if command == 'save':
            mb.save()
        elif command == 'load':
            mb.load()
        else:
            raise exceptions.ArgMismatchException(
                "Unknown command: " + command)

    except exceptions.ExitCleanException:
        exit(1)
    except exceptions.ArgMismatchException as a:
        print('Argument mismatch: ' + str(a))
        exit(2)
    except exceptions.TestException as e:
        print('Fatal error: ' + str(e))
        exit(2)
