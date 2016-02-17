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

import time
import importlib
import pycurl
from StringIO import StringIO
from urllib import urlencode
from subprocess import Popen
import requests
import json

from common.CLI import LinuxCLI


def terminate_process(process, signal='TERM'):
    """
    Poll and terminate a process if it is still running.  If it doesn't exit
    within 5 seconds, send a SIGKILL signal to the process.
    :type process: Popen
    :return:
    """
    LinuxCLI().cmd('pkill -s ' + str(process.pid) + ' -' + signal)


def get_class_from_fqn(fqn):
    # Module name is the whole string, while class name is the last name after the last dot (.)
    mod_name = fqn
    class_name = fqn.split('.')[-1]

    module = importlib.import_module(mod_name)
    impl_class = getattr(module, class_name)
    return impl_class


def curl_get(url):
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    body = buffer.getvalue()
    return body


def curl_post(url, json_data=None, filename=None):
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    if json_data:
        c.setopt(c.POSTFIELDS, json.dumps(json_data))
    if filename:
        c.setopt(c.HTTPPOST, [('fileupload', (c.FORM_FILE, file))])
    c.perform()
    c.close()
    body = buffer.getvalue()
    return body


def curl_put(url, json_data=None, filename=None):
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
    if json_data:
        c.setopt(c.POSTFIELDS, json.dumps(json_data))
    if filename:
        c.setopt(c.HTTPPOST, [('fileupload', (c.FORM_FILE, file))])
    c.perform()
    c.close()
    body = buffer.getvalue()
    return body


def curl_delete(url):
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
    c.perform()
    c.close()
    body = buffer.getvalue()
    return body
