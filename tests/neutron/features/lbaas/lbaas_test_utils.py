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

import logging
import math
import time

from TSM.NeutronTestCase import GuestData
from TSM.NeutronTestCase import NetData
from TSM.NeutronTestCase import NeutronTestCase
from TSM.NeutronTestCase import RouterData
from common.EchoServer import DEFAULT_ECHO_PORT

from collections import namedtuple

LBNetData = namedtuple('LBNetData', 'lbaas member pinger router member_vms')

NUM_PACKETS_TO_SEND = 50
DEFAULT_POOL_PORT = DEFAULT_ECHO_PORT


def create_lb_member_net(tc,
                         lbaas_cidr='192.168.22.0/24',
                         member_cidr='192.168.33.0/24',
                         num_members=2,
                         create_pinger_net=True,
                         pinger_cidr='192.168.55.0/24'):
    """
    :type tc: NeutronTestCase
    :type lbaas_cidr: str
    :type member_cidr: str
    :type num_members: int
    :type create_pinger_net: bool
    :type pinger_cidr: str
    """
    if not tc.LOG:
        tc.LOG = logging.getLogger('lbaas_util_logger')

    member_data = None
    lbaas_data = None
    pinger_data = None
    router_data = None
    members = []
    lbn_data = None
    router = None
    router_ifs = []
    try:
        # Create pool net/subnet
        lbaas_net = tc.api.create_network({'network': {'name': 'lbaas_net',
                                                       'tenant_id': 'admin'}})['network']
        lbaas_subnet = tc.api.create_subnet({'subnet': {'name': 'lbaas_sub',
                                                        'network_id': lbaas_net['id'],
                                                        'ip_version': 4, 'cidr': lbaas_cidr,
                                                        'tenant_id': 'admin'}})['subnet']
        tc.LOG.debug('Created subnet for LBaaS pool: ' + str(lbaas_subnet))
        lbaas_data = NetData(lbaas_net, lbaas_subnet)

        # If member net is different, create member net/subnet
        if member_cidr != lbaas_cidr:
            member_net = tc.api.create_network({'network': {'name': 'member_net',
                                                            'tenant_id': 'admin'}})['network']
            member_subnet = tc.api.create_subnet({'subnet': {'name': 'member_sub',
                                                             'network_id': member_net['id'],
                                                             'ip_version': 4, 'cidr': member_cidr,
                                                             'tenant_id': 'admin'}})['subnet']
            tc.LOG.debug('Created subnet for members: ' + str(member_subnet))
            member_data = NetData(member_net, member_subnet)

        else:
            member_data = NetData(lbaas_net, lbaas_subnet)

        if create_pinger_net:
            pinger_net = tc.api.create_network({'network': {'name': 'pinger_net',
                                                            'tenant_id': 'admin'}})['network']
            pinger_subnet = tc.api.create_subnet({'subnet': {'name': 'pinger_sub',
                                                             'network_id': pinger_net['id'],
                                                             'ip_version': 4, 'cidr': pinger_cidr,
                                                             'tenant_id': 'admin'}})['subnet']

            tc.LOG.debug('Created subnet for pingers: ' + str(pinger_subnet))
            pinger_data = NetData(pinger_net, pinger_subnet)

        # Create pool router
        router = tc.api.create_router({'router': {'name': 'lbaas_router',
                                                  'external_gateway_info':
                                                      {'network_id': tc.pub_network['id']},
                                                  'tenant_id': 'admin'}})['router']

        router_ifs = []
        tc.LOG.debug('Created subnet router for LBaaS pool: ' + str(router))
        # Add gw for pool subnet
        iface = tc.api.add_interface_router(router['id'], {'subnet_id': lbaas_data.subnet['id']})
        tc.LOG.debug('Created subnet interface for LBaaS pool net: ' + str(iface))
        router_ifs.append(iface)
        if member_cidr != lbaas_cidr:
            # Add gw for member subnet
            iface2 = tc.api.add_interface_router(router['id'], {'subnet_id': member_data.subnet['id']})
            tc.LOG.debug('Created subnet interface for member net: ' + str(iface2))
            router_ifs.append(iface2)
        if create_pinger_net:
            # Add gw for pinger subnet
            iface3 = tc.api.add_interface_router(router['id'], {'subnet_id': pinger_data.subnet['id']})
            tc.LOG.debug('Created subnet interface for pinger net: ' + str(iface3))
            router_ifs.append(iface3)
        router_data = RouterData(router, router_ifs)

        # Create member VMs
        for i in range(0, num_members):
            port = tc.api.create_port({'port': {'name': 'port1',
                                                'network_id': member_data.network['id'],
                                                'admin_state_up': True,
                                                'tenant_id': 'admin'}})['port']
            tc.LOG.debug('Created port1: ' + str(port))
            ip = port['fixed_ips'][0]['ip_address']
            vm = tc.vtm.create_vm(ip=ip, mac=port['mac_address'],
                                  gw_ip=member_data.subnet['gateway_ip'])
            vm.plugin_vm('eth0', port['id'])
            members.append(GuestData(port, vm, ip))

        lbn_data = LBNetData(lbaas_data,
                             member_data,
                             pinger_data,
                             router_data,
                             members)

    except Exception as e:
        broken_router_data = RouterData(router, router_ifs)
        clear_lbaas_member_net(tc,
                               lbaas_data, member_data, pinger_data, broken_router_data,
                               members, throw_on_fail=False)
        tc.LOG.fatal('Error setting up topology: ' + str(e))
        raise e

    return lbn_data


def clear_lbaas_data(tc, lbn_data, throw_on_fail=False):
    if not lbn_data:
        return

    clear_lbaas_member_net(tc,
                           lbn_data.lbaas, lbn_data.member, lbn_data.pinger,
                           lbn_data.router,
                           lbn_data.member_vms,
                           throw_on_fail)


def clear_lbaas_member_net(tc,
                           lbaas_data, member_data, pinger_data,
                           router_data, members, throw_on_fail=False):
    """
    :type tc: NeutronTestCase
    :type lbaas_data: NetworkData
    :type member_data: NetworkData
    :type pinger_data: NetworkData
    :type router_data: RouterData
    :type members: list[GuestData]

    :return:
    """
    try:
        for gd in members:
            if gd:
                gd.vm.stop_echo_server(ip=gd.ip, port=DEFAULT_POOL_PORT)
                tc.cleanup_vms([(gd.vm, gd.port)])
        if router_data:
            tc.api.update_router(router_data.router['id'], {'router': {'routes': None}})
            for iface in router_data.if_list:
                tc.api.remove_interface_router(router_data.router['id'], iface)
                tc.LOG.debug('Deleted router iface: ' + str(iface))
            tc.api.delete_router(router_data.router['id'])
            tc.LOG.debug('Deleted router: ' + router_data.router['id'])
        if lbaas_data and lbaas_data.network:
            if lbaas_data.subnet:
                tc.api.delete_subnet(lbaas_data.subnet['id'])
                tc.LOG.debug('Deleted LBaaS subnet: ' + lbaas_data.subnet['id'])
            tc.api.delete_network(lbaas_data.network['id'])
            tc.LOG.debug('Deleted LBaaS network: ' + lbaas_data.network['id'])
        if pinger_data and pinger_data.network:
            if pinger_data.subnet:
                tc.api.delete_subnet(pinger_data.subnet['id'])
                tc.LOG.debug('Deleted Pinger subnet: ' + pinger_data.subnet['id'])
            tc.api.delete_network(pinger_data.network['id'])
            tc.LOG.debug('Deleted Pinger network: ' + pinger_data.network['id'])
        if member_data.network and \
           member_data.network['id'] != lbaas_data.network['id']:
            if member_data.subnet:
                tc.api.delete_subnet(member_data.subnet['id'])
                tc.LOG.debug('Deleted Member subnet: ' + member_data.subnet['id'])
            tc.api.delete_network(member_data.network['id'])
            tc.LOG.debug('Deleted Member network: ' + member_data.network['id'])
    except Exception as e:
        if throw_on_fail:
            tc.fail("Failed cleaning up LBaaS topo: " + str(e))
        else:
            tc.LOG.fatal("Failed cleaning up LBaaS topo: " + str(e))


def send_packets_to_vip(tc, member_list, pinger, vip, num_packets=NUM_PACKETS_TO_SEND,
                        to_port=DEFAULT_POOL_PORT):
    """
    :type tc: NeutronTestCase
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
            g.vm.start_echo_server(ip=g.ip, port=to_port, echo_data=g.vm.vm_host.name)
            host_replies[g.vm.vm_host.name] = 0
        host_replies["NO_RESPONSE"] = 0

        time.sleep(1)

        tc.LOG.debug("Sending " + str(num_packets) + " TCP count from LBaaS VM to VIP:" + str(vip))
        streak_no_response = 0
        for i in range(0, num_packets):
            reply = pinger.vm.send_echo_request(dest_ip=str(vip), dest_port=to_port,
                                                echo_request='ping').strip()
            tc.LOG.debug('Got reply from echo-server: ' + reply)
            replying_vm = reply.split(':')[-1]
            if replying_vm != '':
                if replying_vm not in host_replies:
                    if "MISMATCH_RESPONSE_" + replying_vm not in host_replies:
                        host_replies["MISMIATCHED_RESPONSE_" + replying_vm] = 0
                    host_replies["MISMIATCHED_RESPONSE_" + replying_vm] += 1
                else:
                    host_replies[replying_vm] += 1
                streak_no_response = 0
            else:
                host_replies["NO_RESPONSE"] += 1
                streak_no_response += 1
                if streak_no_response >= 5:
                    tc.LOG.fatal("5 missed packets in a row: giving up")
                    # Fill in the rest of the "NO_RESPONSE" (minus one because
                    # we already marked this packet as NO_RESPONSE)
                    host_replies["NO_RESPONSE"] += num_packets - i - 1
                    break
    finally:
        for g in member_list:
            g.vm.stop_echo_server(ip=g.ip, port=to_port)

    return host_replies


def check_host_replies_against_rr_baseline(tc, member_list, host_replies,
                                           total_expected=0, identifier=None,
                                           check_against_round_robin=False):
    """
    :type tc: NeutronTestCase
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
        failure_conditions.append("VM failed to respond [count: " + str(failed_response) + ']')

    for vm in [m for m in host_replies.iterkeys() if m.startswith("MISMIATCHED_RESPONSE_")]:
        mismatch_name = vm[21:]
        failure_conditions.append('Received [' + str(host_replies[vm]) +
                                  '] mismatched and unexpected reply(ies): ' + mismatch_name)

    total_packet_count = sum([c for k, c in host_replies.iteritems() if k != "NO_RESPONSE"])

    tc.LOG.debug("Got total of " + str(total_packet_count) + " packets")
    if total_expected != total_packet_count:
        failure_conditions.append("Didn't receive expected number of responses: " +
                                  str(total_packet_count) + ", expected: " + str(total_expected))

    # Acceptable delta is +/-50% of the expected average
    baseline_average = float(float(total_expected) / float(len(member_list)))
    acceptable_delta = float(float(total_expected) / float(2 * len(member_list)))

    for h in member_list:
        name = h.vm.vm_host.name
        count = host_replies[name]
        tc.LOG.debug("Got " + str(count) + " packets on VM: " + name)

        if name not in host_replies or host_replies[name] == 0:
            failure_conditions.append("Member never responded: " + name)

        # round robin means the packets should be relatively evenly distributed
        # but it's not perfect, so allow a leeway for each host
        if check_against_round_robin:
            if count < math.floor(baseline_average - acceptable_delta) or \
               count > math.ceil(baseline_average + acceptable_delta):
                failure_conditions.append("Number of packets received outside tolerance (vm: " +
                                          name + ", num_replies: " + str(count) +
                                          "), (avg: " + str(baseline_average) +
                                          ", delta: " + str(acceptable_delta) + ")")

    if len(failure_conditions) > 0:
        fail_str = "Failed packet check" + (" for [" + identifier + "]" if identifier else "")
        fail_str += " because:\n* " + "\n* ".join(failure_conditions)
        tc.fail(fail_str)
