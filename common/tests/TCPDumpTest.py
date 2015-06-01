__author__ = 'micucci'

import unittest
from common.TCPDump import *
from common.PCAPPacket import *
from common.PCAPRules import *
from common.TCPSender import TCPSender

import multiprocessing

class TCPDumpTest(unittest.TestCase):

    def test_sniff_all_host_packet(self):
        tcpd = TCPDump()

        out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"',
                             return_output=True)
        iface = out.split()[0].rstrip()
        data_queue = tcpd.start_capture(timeout=10, interface=iface, count=1)

        ret = data_queue.get()
        tcpd.stop_capture()

        packet = ret[0].get_data()

        self.assertTrue('ethernet'in packet)

        print ret

    def test_sniff_simple_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"',
                             return_output=True)
        iface = out.split()[0].rstrip()

        data_queue = tcpd.start_capture(timeout=10, interface='any', count=1,
                           pcap_filter=PCAP_And(
                               [
                                   PCAP_Host('localhost', proto='ip', dest=True),
                                   PCAP_Port(80, proto='tcp', dest=True)
                               ]
                           ))

        tcps.start_send(interface=iface, packet_type='tcp', count=1, dest_ip='127.0.0.1', dest_port=80)

        ret = data_queue.get()
        tcpd.stop_capture()

        self.assertTrue(len(ret) != 0)

        packet = ret[0].get_data()

        print ret

    def test_sniff_complex_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"',
                             return_output=True)
        iface = out.split()[0].rstrip()

        data_queue = tcpd.start_capture(timeout=10, interface=iface, count=1,
                           pcap_filter=PCAP_Or(
                               [
                                   PCAP_And(
                                       [
                                           PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                           PCAP_Port(6015, proto='tcp', source=True),
                                           PCAP_Port(6055, proto='tcp', dest=True),
                                           PCAP_LessThanEqual('len', 1500)
                                       ]
                                   ),
                                   PCAP_And(
                                       [
                                           PCAP_Port(80, proto='tcp', dest=True),
                                           PCAP_PortRange(8000, 8500, proto='tcp', source=True),
                                           PCAP_LessThanEqual('len', 1500)
                                       ]
                                   ),
                               ]
                           ))

        tcps.start_send(interface=iface, packet_type='tcp', count=1, source_ip='127.0.0.1',
                        dest_ip='127.0.0.1', dest_port=6055, source_port=6015)

        ret = data_queue.get()
        tcpd.stop_capture()

        packet = ret[0].get_data()

        print ret


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(TCPDumpTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

