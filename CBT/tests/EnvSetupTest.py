__author__ = 'micucci'

import unittest
from CBT.EnvSetup import EnvSetup

class MyTestCase(unittest.TestCase):
    def test_neutron_install(self):
        EnvSetup.install_neutron_client()


if __name__ == '__main__':
    unittest.main()
