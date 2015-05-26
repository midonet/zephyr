__author__ = 'micucci'

import unittest
from common.CLI import *

class CLITest(unittest.TestCase):
    def test_something(self):
        pass


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(CLITest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

