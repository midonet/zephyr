# Copyright 2016 Midokura SARL
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

import unittest
from zephyr.common import utils


class UtilsTest(unittest.TestCase):
    def test_check_string_for_tag(self):
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "foo"))
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "fo"))
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "bar"))
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "foo bar"))
        self.assertTrue(
            utils.check_string_for_tag("foo foo baz", "foo", 2))
        self.assertTrue(
            utils.check_string_for_tag("foo bar foo", "foo", 2))
        self.assertTrue(
            utils.check_string_for_tag("foo bar bar", "bar", 2))
        self.assertTrue(
            utils.check_string_for_tag("foo foo baz", "foo", 1, exact=False))
        self.assertTrue(
            utils.check_string_for_tag("foo foo foo", "foo", 2, exact=False))
        self.assertTrue(
            utils.check_string_for_tag("foo foo baz", "foo", 2, exact=False))
        self.assertTrue(
            utils.check_string_for_tag("foo foo foo", "foo", 3, exact=False))

        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "bamf"))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "foot"))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "foo", 2))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "baz", 3))
        self.assertFalse(
            utils.check_string_for_tag("foo bar bar", "foo bar", 2))
        self.assertFalse(
            utils.check_string_for_tag("foo barfoo barfoo", "foo barfoo", 2))
        self.assertFalse(
            utils.check_string_for_tag("foo foo baz", "foo", 1))
        self.assertFalse(
            utils.check_string_for_tag("foo foo baz", "foo", 3, exact=False))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "bar", 2, exact=False))
        self.assertFalse(
            utils.check_string_for_tag("foo barfoo barfoo", "foo barfoo", 2,
                                       exact=False))

        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "bamf", 0))
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "bamf", 0, exact=False))
        self.assertTrue(
            utils.check_string_for_tag("foo bar baz", "foo", 0, exact=False))

        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "foo", 0))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "bar", 0))
        self.assertFalse(
            utils.check_string_for_tag("foo bar baz", "baz", 0))

utils.run_unit_test(UtilsTest)
