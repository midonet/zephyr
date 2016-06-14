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


class UnderlayHost(object):
    def __init__(self, name):
        self.name = name
        self.underlay_host_obj = None
        self.underlay_type = None

    def attach_underlay_host(self, type, host_obj):
        self.underlay_host_obj = host_obj
        self.underlay_type = type

    def get_resource(self):
        pass

    def create_vm(self):
        pass
