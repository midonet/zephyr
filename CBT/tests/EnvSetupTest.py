__author__ = 'micucci'

import unittest
import CBT.EnvSetup as env
from CBT.EnvSetupInstallers import *
import CBT.VersionConfig as version_config

class EnvSetupTest(unittest.TestCase):
    def test_repo_info(self):
        repo = DebianPackageRepo('http', 'test-server', 'test1')
        repo.create_repo_file()
        repo.install_package('test-pkg', 'thisVersion')

    def test_component_info(self):
        repo = DebianPackageRepo('http', 'test-server', 'test1')
        comp = MidonetComponentInstaller()
        comp.install_packages(repo, 'thisVersion')

    def test_env_component_install_default(self):
        env.install_component()

    def test_env_component_install_param(self):
        env.install_component(component='midonet', server='test-server', distribution='debug',
                              exact_version='thisVersion')


pass
# Skip for now
#from CBT.UnitTestRunner import run_unit_test
#run_unit_test(EnvSetupTest)