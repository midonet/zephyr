__author__ = 'micucci'
# Copyright 2015 Midokura SARL
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


class MDTSException(Exception):
    def __init__(self, info):
        self.info = info
        """ :type: str"""

    def __str__(self):
        return repr(self.info)


class HostNotFoundException(MDTSException):
    def __init__(self, info):
        super(HostNotFoundException, self).__init__(info)


class HostAlreadyStartedException(MDTSException):
    def __init__(self, info):
        super(HostAlreadyStartedException, self).__init__(info)


class ObjectNotFoundException(MDTSException):
    def __init__(self, info):
        super(ObjectNotFoundException, self).__init__(info)


class ObjectAlreadyAddedException(MDTSException):
    def __init__(self, info):
        super(ObjectAlreadyAddedException, self).__init__(info)


class ArgMismatchException(MDTSException):
    def __init__(self, info):
        super(ArgMismatchException, self).__init__(info)


class SubprocessFailedException(MDTSException):
    def __init__(self, info):
        super(SubprocessFailedException, self).__init__(info)


class ExitCleanException(MDTSException):
    def __init__(self):
        super(ExitCleanException, self).__init__('')


class SocketException(MDTSException):
    def __init__(self, info):
        super(SocketException, self).__init__(info)


class InvallidConfigurationException(MDTSException):
    def __init__(self, config, reason):
        super(InvallidConfigurationException, self).__init__(reason + " in config <" + str(config) + ">")


class PacketParsingException(MDTSException):
    def __init__(self, info, fatal=True):
        super(PacketParsingException, self).__init__(info)
        self.fatal = fatal