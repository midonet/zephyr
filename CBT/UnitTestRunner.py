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

import unittest
import xmlrunner
import os


def run_unit_test(test_case_name):
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case_name)
    xml_output = False
    xml_output_dir = ''
    if 'ZEPHYR_TEST_JUNIT_OUTDIR' in os.environ:
        xml_output_dir = os.environ['ZEPHYR_TEST_JUNIT_OUTDIR']
        xml_output = True

    if not xml_output:
        try:
            unittest.TextTestRunner(verbosity=2).run(suite)
        except Exception as e:
            print('Exception: ' + e.message + ', ' + str(e.args))
    else:
        import xmlrunner
        xmlrunner.XMLTestRunner(output=xml_output_dir).run(suite)
