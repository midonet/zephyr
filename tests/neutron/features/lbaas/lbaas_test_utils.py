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

from collections import namedtuple
import math
import time

from zephyr.common.echo_server import DEFAULT_ECHO_PORT
from zephyr.common.exceptions import ObjectAlreadyAddedException
from zephyr.common.exceptions import ObjectNotFoundException
from zephyr.tsm.neutron_test_case import GuestData
from zephyr.tsm.neutron_test_case import NeutronTestCase

LBNetData = namedtuple('LBNetData', 'lbaas member pinger router member_vms')

NUM_PACKETS_TO_SEND = 50
DEFAULT_POOL_PORT = DEFAULT_ECHO_PORT


class LBaaSTestCase(NeutronTestCase):
    def __init__(self, method_name='runTest'):
        super(LBaaSTestCase, self).__init__(method_name)
        self.topos = {}
        """ :type: dict[str, dict[str, dict[str, dict[str, str]]] """

        self.pingers = []
        """ :type: list[GuestData] """

        self.pool_ids = []
        """ :type: list[str] """
        self.vip_ids = []
        """ :type: list[str] """
        self.health_monitor_ids = []
        """ :type: list[str] """
        self.associated_health_monitors = []
        """ :type: list[(str,str)]"""
        self.member_ids = []
        """ :type: list[str] """

    def create_pinger_net(self, name='main', cidr='192.168.55.0/24',):
        """
        :type cidr: str
        """
        if name not in self.topos:
            self.topos[name] = {}

        if 'pinger' in self.topos[name]:
            raise ObjectAlreadyAddedException(
                'Pinger topo already added for: ' + name)

        pinger_net = self.create_network(name='pinger_net')
        pinger_subnet = self.create_subnet(name='pinger_sub',
                                           net_id=pinger_net['id'],
                                           cidr=cidr)

        self.LOG.debug('Created subnet for pingers: ' + str(pinger_subnet))
        self.topos[name]['pinger'] = {'network': pinger_net,
                                      'subnet': pinger_subnet}

    def create_lbaas_net(self, name='main', cidr='192.168.22.0/24'):
        """
        :type cidr: str
        """
        if name not in self.topos:
            self.topos[name] = {}

        if 'lbaas' in self.topos[name]:
            raise ObjectAlreadyAddedException(
                'LBaaS topo already added for: ' + name)

        lbaas_net = self.create_network(name='lbaas_net')
        lbaas_subnet = self.create_subnet(name='lbaas_sub',
                                          net_id=lbaas_net['id'],
                                          cidr=cidr)

        self.LOG.debug('Created subnet for lbaass: ' + str(lbaas_subnet))
        self.topos[name]['lbaas'] = {'network': lbaas_net,
                                     'subnet': lbaas_subnet}

    def create_member_net(self, name='main', cidr='192.168.33.0/24'):
        """
        :type cidr: str
        """
        if name not in self.topos:
            self.topos[name] = {}

        if 'member' in self.topos[name]:
            raise ObjectAlreadyAddedException(
                'Member topo already added for: ' + name)

        member_net = self.create_network(name='member_net')
        member_subnet = self.create_subnet(name='member_sub',
                                           net_id=member_net['id'],
                                           cidr=cidr)

        self.LOG.debug('Created subnet for members: ' + str(member_subnet))
        self.topos[name]['member'] = {'network': member_net,
                                      'subnet': member_subnet}

    def create_lb_router(self, name='main', gw_net_id=None):
        # Create pool router
        if name not in self.topos:
            self.topos[name] = {}

        if 'router' in self.topos[name]:
            raise ObjectAlreadyAddedException('Router already added for: ' +
                                              name)

        router = self.create_router(
            name=name + '_lb_router',
            pub_net_id=gw_net_id)

        self.LOG.debug('Created subnet router for LBaaS pool: ' +
                       str(router))

        if 'lbaas' in self.topos[name]:
            # Add gw for pool subnet
            iface = self.create_router_interface(
                router_id=router['id'],
                sub_id=self.topos[name]['lbaas']['subnet']['id'])
            self.LOG.debug('Created subnet interface for LBaaS pool net: ' +
                           str(iface))

        if 'member' in self.topos[name]:
            # Add gw for member subnet
            iface = self.create_router_interface(
                router_id=router['id'],
                sub_id=self.topos[name]['member']['subnet']['id'])
            self.LOG.debug('Created subnet interface for LBaaS member net: ' +
                           str(iface))

        if 'pinger' in self.topos[name]:
            # Add gw for pinger subnet
            iface = self.create_router_interface(
                router_id=router['id'],
                sub_id=self.topos[name]['pinger']['subnet']['id'])
            self.LOG.debug('Created subnet interface for pinger net: ' +
                           str(iface))

        self.topos[name]['router'] = router
        return router

    def create_member_vms(self,
                          num_members,
                          name='main',
                          net='member',
                          hv_host=None):
        """
        Create num_member VMs on the net/subnet provided by 'net'
        :type num_members: int
        :type name: str
        :type net: str
        :type hv_host: str
        """
        if name not in self.topos or net not in self.topos[name]:
            raise ObjectNotFoundException("Name or net not found: " +
                                          name + ", " + net)
        net_id = self.topos[name][net]['network']['id']
        gw_ip = self.topos[name][net]['subnet']['gateway_ip']

        ret = []
        new_name = name.translate(None, 'aeiou')
        for i in range(0, num_members):
            ret.append(GuestData(*self.create_vm_server(
                name='m_' + new_name + '_' + str(i),
                net_id=net_id,
                gw_ip=gw_ip,
                hv_host=hv_host)))
        return ret

    def create_pinger_vm(self,
                         name='main',
                         net='pinger',
                         hv_host=None):
        """
        Create a VM on the pinger net/subnet provided by 'net'
        (pinger_net is default)
        :type name: str
        :type net: str
        :type hv_host: str
        """
        if name not in self.topos or net not in self.topos[name]:
            raise ObjectNotFoundException("Name or net not found: " +
                                          name + ", " + net)
        net_id = self.topos[name][net]['network']['id']
        gw_ip = self.topos[name][net]['subnet']['gateway_ip']
        new_name = name.translate(None, 'aeiou')
        pinger = GuestData(*self.create_vm_server(
            name='p_' + new_name,
            net_id=net_id,
            gw_ip=gw_ip,
            hv_host=hv_host))
        self.pingers.append(pinger)
        return pinger

    def clear_lbaas_data(self, throw_on_fail=False):
        """
        :type throw_on_fail: bool
        :return:
        """
        try:
            while self.vip_ids:
                vip = self.vip_ids.pop()
                self.LOG.debug('Deleting VIP: ' + str(vip))
                self.api.delete_vip(vip)
            while self.member_ids:
                member = self.member_ids.pop()
                self.LOG.debug('Deleting member: ' + str(member))
                self.api.delete_member(member)
            while self.associated_health_monitors:
                hm, pool = self.associated_health_monitors.pop()
                self.LOG.debug('Disassociating health monitor: ' + str(hm))
                self.api.disassociate_health_monitor(pool, hm)
            while self.health_monitor_ids:
                hm = self.health_monitor_ids.pop()
                self.LOG.debug('Deleting health monitor: ' + str(hm))
                self.api.delete_health_monitor(hm)
            while self.pool_ids:
                pool = self.pool_ids.pop()
                self.LOG.debug('Deleting pool: ' + str(pool))
                self.api.delete_pool(pool)
        except Exception as e:
            if throw_on_fail:
                self.fail("Failed cleaning up LBaaS topo: " + str(e))
            else:
                self.LOG.fatal("Failed cleaning up LBaaS topo: " + str(e))

    def create_pool(self, subnet_id, name='pool1', protocol='TCP',
                    lb_method='ROUND_ROBIN', tenant_id='admin'):
        pool = self.api.create_pool(
            {'pool': {'name': name,
                      'protocol': protocol,
                      'subnet_id': subnet_id,
                      'lb_method': lb_method,
                      'admin_state_up': True,
                      'tenant_id': tenant_id}})['pool']
        self.LOG.debug('Created LBaaS Pool: ' + str(pool))
        self.pool_ids.append(pool['id'])
        return pool

    def update_pool(self, subnet_id, name='pool1', protocol='TCP',
                    lb_method='ROUND_ROBIN', tenant_id='admin'):
        pass

    def delete_pool(self, pool_id):
        self.api.delete_pool(pool_id)
        self.pool_ids.remove(pool_id)

    def create_health_monitor(self, proto_type='TCP', delay=3,
                              timeout=1, max_retries=2,
                              tenant_id='admin'):
        hm = self.api.create_health_monitor(
            {'health_monitor': {'tenant_id': tenant_id,
                                'type': proto_type,
                                'delay': delay,
                                'timeout': timeout,
                                'max_retries': max_retries}})['health_monitor']
        self.LOG.debug('Created Health Monitor: ' + str(hm))
        self.health_monitor_ids.append(hm['id'])
        return hm

    def associate_health_monitor(self, hm_id, pool_id, tenant_id='admin'):
        self.api.associate_health_monitor(
            pool_id, {'health_monitor': {'tenant_id': tenant_id,
                                         'id': hm_id}})
        self.LOG.debug("Associated Health Monitor to pool: " +
                       str(hm_id) + "=>" + str(pool_id))
        self.associated_health_monitors.append((hm_id, pool_id))

    def delete_health_monitor(self, hm_id):
        self.api.delete_health_monitor(hm_id)
        self.health_monitor_ids.remove(hm_id)

    def create_vip(self, pool_id, subnet_id,
                   name='vip1', protocol='TCP',
                   protocol_port=DEFAULT_POOL_PORT,
                   tenant_id='admin'):
        vip = self.api.create_vip(
            {'vip': {'name': name,
                     'subnet_id': subnet_id,
                     'protocol': protocol,
                     'protocol_port': protocol_port,
                     'pool_id': pool_id,
                     'tenant_id': tenant_id}})['vip']
        self.LOG.debug('Created LBaaS VIP: ' + str(vip))
        self.vip_ids.append(vip['id'])
        return vip

    def delete_vip(self, vip_id):
        self.api.delete_vip(vip_id)
        self.vip_ids.remove(vip_id)

    def create_member(self, pool_id, ip_addr,
                      protocol_port=DEFAULT_POOL_PORT,
                      tenant_id='admin'):

        member = self.api.create_member(
            {'member': {'address': ip_addr,
                        'protocol_port': protocol_port,
                        'pool_id': pool_id,
                        'tenant_id': tenant_id}})['member']
        self.LOG.debug('Created LBaaS member:' + str(member))
        self.member_ids.append(member['id'])
        return member

    def delete_member(self, member_id):
        self.api.delete_member(member_id)
        self.member_ids.remove(member_id)

    def send_packets_to_vip(self, member_list, pinger,
                            vip, num_packets=NUM_PACKETS_TO_SEND,
                            to_port=DEFAULT_POOL_PORT):
        """
        :type self: NeutronTestCase
        :type member_list: list[GuestData]
        :type pinger: GuestData
        :type vip: str
        :type num_packets: int
        :type to_port: int
        :return:
        """
        host_replies = {}
        """ :type: dict[str, int] """
        try:
            for g in member_list:
                g.vm.start_echo_server(
                    ip_addr=g.ip, port=to_port,
                    echo_data=g.vm.vm_host.name)
                host_replies[g.vm.vm_host.name] = 0
            host_replies["NO_RESPONSE"] = 0

            time.sleep(1)

            self.LOG.debug("Sending " + str(num_packets) +
                           " TCP count from LBaaS VM to VIP:" + str(vip))
            streak_no_response = 0
            for i in range(0, num_packets):
                reply = pinger.vm.send_echo_request(
                    dest_ip=str(vip), dest_port=to_port,
                    echo_request='ping').strip()
                self.LOG.debug('Got reply from echo-server: ' + reply)
                replying_vm = reply.split(':')[-1]
                if replying_vm != '':
                    if replying_vm not in host_replies:
                        if "MISMATCH_RESPONSE_" + replying_vm \
                                not in host_replies:
                            host_replies["MISMIATCHED_RESPONSE_" +
                                         replying_vm] = 0
                        host_replies["MISMIATCHED_RESPONSE_" +
                                     replying_vm] += 1
                    else:
                        host_replies[replying_vm] += 1
                    streak_no_response = 0
                else:
                    host_replies["NO_RESPONSE"] += 1
                    streak_no_response += 1
                    if streak_no_response >= 5:
                        self.LOG.fatal("5 missed packets in a row: giving up")
                        # Fill in the rest of the "NO_RESPONSE"
                        # (minus one because we already marked
                        # this packet as NO_RESPONSE)
                        host_replies["NO_RESPONSE"] += num_packets - i - 1
                        break
        finally:
            for g in member_list:
                g.vm.stop_echo_server(ip_addr=g.ip, port=to_port)

        return host_replies

    def check_host_replies_against_rr_baseline(
            self, member_list, host_replies,
            total_expected=0, identifier=None,
            check_against_round_robin=False):
        """
        :type self: NeutronTestCase
        :type member_list: list[GuestData]
        :type host_replies: dict[str, int]
        :type total_expected: int
        :type identifier: str
        :return:
        """

        failure_conditions = []

        if total_expected == 0:
            total_expected = NUM_PACKETS_TO_SEND

        failed_response = host_replies["NO_RESPONSE"]
        if failed_response > 0:
            failure_conditions.append("VM failed to respond [count: " +
                                      str(failed_response) + ']')

        for vm in [m for m in host_replies.iterkeys()
                   if m.startswith("MISMIATCHED_RESPONSE_")]:
            mismatch_name = vm[21:]
            failure_conditions.append(
                'Received [' + str(host_replies[vm]) +
                '] mismatched and unexpected reply(ies): ' +
                mismatch_name)

        total_packet_count = \
            sum([c for k, c in host_replies.iteritems()
                 if k != "NO_RESPONSE"])

        self.LOG.debug("Got total of " + str(total_packet_count) + " packets")
        if total_expected != total_packet_count:
            failure_conditions.append(
                "Didn't receive expected number of responses: " +
                str(total_packet_count) + ", expected: " +
                str(total_expected))

        # Acceptable delta is +/-50% of the expected average
        baseline_average = float(float(total_expected) /
                                 float(len(member_list)))
        acceptable_delta = float(float(total_expected) /
                                 float(2 * len(member_list)))

        for h in member_list:
            name = h.vm.vm_host.name
            count = host_replies[name]
            self.LOG.debug("Got " + str(count) + " packets on VM: " + name)

            if name not in host_replies or host_replies[name] == 0:
                failure_conditions.append("Member never responded: " + name)

            # round robin means the packets should be relatively
            # evenly distributed but it's not perfect, so allow
            # a leeway for each host
            if check_against_round_robin:
                if count < math.floor(baseline_average - acceptable_delta) or \
                   count > math.ceil(baseline_average + acceptable_delta):
                    failure_conditions.append(
                        "Number of packets received outside tolerance (vm: " +
                        name + ", num_replies: " + str(count) +
                        "), (avg: " + str(baseline_average) +
                        ", delta: " + str(acceptable_delta) + ")")

        if len(failure_conditions) > 0:
            fail_str = "Failed packet check" + (" for [" + identifier + "]"
                                                if identifier else "")
            fail_str += " because:\n* " + "\n* ".join(failure_conditions)
            self.fail(fail_str)
