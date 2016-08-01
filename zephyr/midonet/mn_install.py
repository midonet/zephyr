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
from zephyr_ptm.ptm.config import version_config as vc

DEFAULT_REPO = "http://builds.midonet.org"


class MidonetInstaller(object):
    def __init__(self, version, repo_url=DEFAULT_REPO,
                 package="stable", debug=False):
        """
        :type version: str
        :type repo_url: str
        :type package: str
        :type debug: bool
        """
        self.version = version
        self.package = package
        self.debug = debug
        self.LOG = logging.getLogger(name="midonet_install")
        file_handler = logging.StreamHandler()
        file_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        self.LOG.addHandler(file_handler)
        distro = vc.get_linux_dist()
        self.cli = cli.LinuxCLI(print_cmd_out=debug)
        self.cli.add_environment_variable(
            "DEBIAN_FRONTEND", "noninteractive")
        if distro == vc.LINUX_UBUNTU:
            self.repo_file = "/etc/apt/sources.list"
            self.repo_line = (
                "deb " + repo_url + "/midonet-" + str(self.version) + " " +
                self.package + " main")
            self.install_str = "apt-get install -y"
            self.uninstall_str = "dpkg -P --force-depends"
            self.repo_prepare = "apt-get update"
        elif distro == vc.LINUX_CENTOS:
            self.repo_file = "/etc/yum.repos.d/midokura.repo"
            # self.repo_line = (
            #    "deb " + repo_url + "/midonet-" + str(self.version) + " " +
            #    self.package + " main")
            self.install_str = "yum install -y"
            self.uninstall_str = "yum remove -y"
            self.repo_prepare = "yum clean all"
        else:
            raise exceptions.ArgMismatchException(
                "Unknown linux distribution: " + distro)

    def remove_repo(self):
        if self.cli.grep_file(self.repo_file, self.repo_line):
            self.LOG.debug(
                self.cli.cmd(
                    'sed -ie "/' +
                    self.repo_line.replace('/', '\\/') + '/d" ' +
                    self.repo_file).stdout)

    def prepare_repo(self):
        if not self.cli.grep_file(self.repo_file, self.repo_line):
            self.cli.write_to_file(
                self.repo_file, self.repo_line + '\n',
                append=True if self.cli.exists(self.repo_file) else False)
            self.LOG.debug(self.cli.cmd(self.repo_prepare).stdout)

    def install(self):
        self.prepare_repo()
        pkgs = vc.ConfigMap.get_configured_parameter(
            param='installed_packages',
            version=vc.parse_midolman_version(self.version))
        self.LOG.debug(
            self.cli.cmd(self.install_str + " " + ' '.join(pkgs)).stdout)

    def uninstall(self):
        pkgs = vc.ConfigMap.get_configured_parameter(
            param='installed_packages',
            version=vc.parse_midolman_version(self.version))
        self.LOG.debug(
            self.cli.cmd(self.uninstall_str + " " + ' '.join(pkgs)).stdout)
        self.remove_repo()


def usage():
    print('Usage: mn_install.py -i <X>.<Y> [-p <pkg_dist>] [-r <repo_url>]')
    print('       mn_install.py -u <X>.<Y> [-p <pkg_dist>] [-r <repo_url>]')
    print('')
    print('   Options:')
    print('     -i, --install <X>.<Y>')
    print('         Install latest-patch midonet packages for version X.Y')
    print('     -u, --uninstall <X>.<Y>')
    print('         Uninstall latest-patch midonet packages for version X.Y')
    print('     [-p, --pkg_dist <pkg_dist>]')
    print('         Use given package distribution instead of "stable"')
    print('     [-r, --repo_url <url>]')
    print('         Use given repo URL instead of "http://builds.midonet.org"')
    print('     -d, --debug')
    print('         Turn on debug logging')


if __name__ == "__main__":

    try:
        arg_map, extra_args = getopt.getopt(
            sys.argv[1:],
            (
                'h'
                'd'
                'i:'
                'u:'
                'p:'
                'r:'
            ),
            [
                'help',
                'install=',
                'uninstall=',
                'pkg_dist=',
                'repo_url=',
                'debug'
            ])

        # Defaults
        version = None
        uninstall = False
        pkg_dist = 'stable'
        repo_url = DEFAULT_REPO
        debug = False

        for arg, value in arg_map:
            if arg in ('-h', '--help'):
                usage()
                sys.exit(0)
            elif arg in ('-i', '--install'):
                uninstall = False
                version = value
            elif arg in ('-u', '--uninstall'):
                uninstall = True
                version = value
            elif arg in ('-p', '--pkg_dist'):
                pkg_dist = value
            elif arg in ('-r', '--repo_url'):
                repo_url = value
            elif arg in ('-d', '--debug'):
                debug = True
            else:
                usage()
                raise exceptions.ArgMismatchException('Invalid argument' + arg)

        mi = MidonetInstaller(
            version=version,
            repo_url=repo_url,
            package=pkg_dist,
            debug=debug)

        if not uninstall:
            mi.install()
        else:
            mi.uninstall()

    except exceptions.ExitCleanException:
        exit(1)
    except exceptions.ArgMismatchException as a:
        print('Argument mismatch: ' + str(a))
        exit(2)
    except exceptions.ObjectNotFoundException as e:
        print('Object not found: ' + str(e))
        exit(2)
