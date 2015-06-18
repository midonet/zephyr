__author__ = 'micucci'
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
from subprocess import Popen

from Exceptions import *


def terminate_process(process):
    """
    Poll and terminate a process if it is still running.  If it doesn't exit
    within 5 seconds, send a SIGKILL signal to the process.
    :type process: Popen
    :return:
    """

    def _poll_loop(p):
        # Wait to get return code
        countdown = 5
        while countdown > 0:
            r = p.poll()
            if r is not None:
                return r
            time.sleep(1)
            countdown -= 1

    ret = process.poll()
    if ret is not None:
        return ret

    process.terminate()

    ret = _poll_loop(process)
    if ret is not None:
        return ret

    # If it didn't die nicely, be a little more insistent
    process.kill()

    _poll_loop(process)
    if ret is not None:
        return ret

    # If it still doesn't die, raise an error
    raise SubprocessFailedException('Process failed to die: ' + process.pid)