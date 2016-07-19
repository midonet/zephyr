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

import importlib
import json
import os
import pycurl
from StringIO import StringIO
import unittest

import xmlrunner


def get_class_from_fqn(fqn):
    # Module name is the whole string until the last dot,
    # while class name is the last name after the last dot (.)
    mod_name = '.'.join(fqn.split('.')[:-1])
    class_name = fqn.split('.')[-1]

    module = importlib.import_module(mod_name)
    impl_class = getattr(module, class_name)
    return impl_class


def curl_get(url):
    cbuffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, cbuffer)
    c.perform()
    c.close()
    body = cbuffer.getvalue()
    return body


def curl_post(url, json_data=None, filename=None):
    cbuffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, cbuffer)
    if json_data:
        c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
        c.setopt(c.POSTFIELDS, json.dumps(json_data))
    if filename:
        c.setopt(c.HTTPPOST, [('fileupload', (c.FORM_FILE, file))])
    c.perform()
    c.close()
    body = cbuffer.getvalue()
    return body


def curl_put(url, json_data=None, filename=None):
    cbuffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, cbuffer)
    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
    if json_data:
        c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
        c.setopt(c.POSTFIELDS, json.dumps(json_data))
    if filename:
        c.setopt(c.HTTPPOST, [('fileupload', (c.FORM_FILE, file))])
    c.perform()
    c.close()
    body = cbuffer.getvalue()
    return body


def curl_delete(url):
    cbuffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, cbuffer)
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    c.perform()
    c.close()
    body = cbuffer.getvalue()
    return body


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
        xmlrunner.XMLTestRunner(output=xml_output_dir).run(suite)


def check_string_for_tag(main_str, tag, num_occur=1, exact=True):
    """
    :type main_str: str
    :type tag: str
    :type num_occur: int
    :type exact: bool
    """
    indx = 0
    for i in range(0, num_occur):
        found_indx = main_str.find(tag, indx)
        if found_indx == -1:
            return False
        indx = found_indx + len(tag)
    if exact:
        found_indx = main_str.find(tag, indx)
        if found_indx != -1:
            return False

    return True


def make_gateway_ip(real_ip):
    # Figure out a default gw based on IP, usually
    # (IP & subnet_mask + 1)
    subnet_mask = [255, 255, 255, 255]
    if real_ip.subnet != "":
        smask = int(real_ip.subnet)
        subnet_mask = []

        current_mask = smask
        for i in range(0, 4):
            if current_mask > 8:
                subnet_mask.append(255)
            else:
                lastmask = 0
                for j in range(0, current_mask):
                    lastmask += pow(2, 8 - (j + 1))
                subnet_mask.append(lastmask)
            current_mask -= 8

    split_ip = real_ip.ip.split(".")
    gw_ip_split = []
    for ip_part in split_ip:
        gw_ip_split.append(int(ip_part) &
                           subnet_mask[len(gw_ip_split)])

    gw_ip_split[3] += 1
    gw_ip = '.'.join(map(lambda x: str(x), gw_ip_split))
    return gw_ip.strip()
