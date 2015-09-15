__author__ = 'micucci'

import unittest
from CBT.EnvSetup import EnvSetup

class MyTestCase(unittest.TestCase):
    def test_neutron_install(self):
        EnvSetup.install_neutron_client()



from CBT.UnitTestRunner import run_unit_test
run_unit_test(FileLocationTest)
t.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))