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

        data_queue = tcpd.start_capture(interface='eth0', count=1)

        ret = data_queue.get(block=True)
        tcpd.stop_capture()

        packet = ret[0].get_data()

        self.assertTrue('ethernet'in packet)
        self.assertTrue('ip'in packet)
        self.assertTrue('tcp'in packet)

        print ret

    def test_sniff_simple_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        data_queue = tcpd.start_capture(timeout=10, interface='any', count=1,
                           pcap_filter=PCAP_And(
                               [
                                   PCAP_Host('localhost', proto='ip', dest=True),
                                   PCAP_Port(80, proto='tcp', dest=True)
                               ]
                           ))

        tcps.start_send(interface='eth0', packet_type='tcp', count=1, dest_ip='127.0.0.1', dest_port=80)

        ret = data_queue.get()
        tcpd.stop_capture()

        packet = ret[0].get_data()

        print ret

    def test_sniff_complex_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        data_queue = tcpd.start_capture(timeout=10, interface='any', count=1,
                           pcap_filter=PCAP_And(
                               [
                                   PCAP_Or(
                                       [
                                           PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                           PCAP_Host('localhost', proto='ether', source=True),
                                           PCAP_LessThanEqual('len', 1500)
                                       ]
                                   ),
                                   PCAP_And(
                                       [
                                           PCAP_Port(80, proto='tcp', source=True, dest=True),
                                           PCAP_PortRange(6000, 6500, proto='tcp', source=True),
                                           PCAP_GreaterThan('len', 1500)
                                       ]
                                   ),
                                   PCAP_Not(PCAP_Net('192.168.0', dest=True))
                               ]
                           ))

        tcps.start_send(interface='eth0', packet_type='tcp', count=1, dest_ip='127.0.0.1', dest_port=80)

        ret = data_queue.get()
        tcpd.stop_capture()

        packet = ret[0].get_data()

        print ret


try:
    suite = unittest.TestLoader().loadTestsFromTestCase(TCPDumpTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
except Exception as e:
    print 'Exception: ' + e.message + ', ' + str(e.args)

