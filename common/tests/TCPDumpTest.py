
import unittest
from common.TCPDump import *
from common.PCAPPacket import *
from common.PCAPRules import *
from common.TCPSender import TCPSender
from common.CLI import LinuxCLI

import multiprocessing

def packet_callback(packet, file_name):
    """
    :type packet: PCAPPacket
    :return:
    """
    with open(file_name, "a" if LinuxCLI().exists(file_name) else "w") as f:
        f.write(packet.to_str())


def send_packet():
    time.sleep(5)
    tcps = TCPSender()
    out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
    lo_iface = out.split()[0].rstrip()
    tcps.start_send(interface=lo_iface, packet_type='tcp', count=3, source_ip='127.0.0.1',
                    dest_ip='127.0.0.1', dest_port=6055, source_port=6015)


class TCPDumpTest(unittest.TestCase):
    def setUp(self):
        time.sleep(2)

    def test_read_packet(self):
        tcpd = TCPDump()

        p = multiprocessing.Process(target=send_packet)
        p.start()
        ret = tcpd._read_packet(interface='any', count=3,
                                save_dump_file=True, save_dump_filename='tcp.out')
        p.join()
        p1 = ret.get(block=False)
        p2 = ret.get(block=False)
        p3 = ret.get(block=False)

        """ :type: PCAPPacket"""
        self.assertTrue(p3 is not None)

    def test_read_packet_buffered(self):
        tcpd = TCPDump()

        out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
        lo_iface = out.split()[0].rstrip()

        p = multiprocessing.Process(target=send_packet)
        p.start()
        ret = tcpd._read_packet(interface=lo_iface, count=3,
                                pcap_filter=PCAP_And(
                                    [
                                        PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                        PCAP_Port(6015, proto='tcp', source=True),
                                        PCAP_Port(6055, proto='tcp', dest=True)
                                    ]
                                ),
                                save_dump_file=True, save_dump_filename='tcp.out')
        p.join()
        p1 = ret.get(block=False).parse()
        p2 = ret.get(block=False).parse()
        p3 = ret.get(block=False).parse()

        """ :type: PCAPPacket"""
        self.assertTrue(p3 is not None)
        self.assertTrue('ethernet' in p3)

    def test_sniff_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()
        try:

            out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
            lo_iface = out.split()[0].rstrip()
            tcpd.start_capture(interface=lo_iface, count=1)
            tcps.start_send(interface=lo_iface, packet_type='tcp', count=1, source_ip='127.0.0.1',
                            dest_ip='127.0.0.1', dest_port=6055, source_port=6015)

            ret = tcpd.wait_for_packets(count=1, timeout=3)

            self.assertEquals(1, len(ret))

            self.assertTrue('ethernet' in ret[0].parse())

        finally:
            tcpd.stop_capture()

    def test_sniff_host_packet_immediate(self):
        tcpd = TCPDump()
        tcps = TCPSender()
        try:

            out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
            lo_iface = out.split()[0].rstrip()
            tcpd.start_capture(interface=lo_iface,
                               pcap_filter=PCAP_And([PCAP_Port(6015, proto='tcp', source=True),
                                                     PCAP_Port(6055, proto='tcp', dest=True)]))
            tcps.start_send(interface=lo_iface, packet_type='tcp', count=10, source_ip='127.0.0.1',
                            dest_ip='127.0.0.1', dest_port=6055, source_port=6015)

            time.sleep(3)
            tcpd.stop_capture()

            ret = tcpd.wait_for_packets(count=0)

            self.assertAlmostEqual(10, len(ret), delta=4)

            self.assertTrue('ethernet' in ret[0].parse())

        finally:
            tcpd.stop_capture()

    def test_sniff_specific_host_packet(self):
        tcpd = TCPDump()
        tcps = TCPSender()
        try:
            out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
            iface = out.split()[0].rstrip()

            tcpd.start_capture(timeout=10, interface=iface, count=1,
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

            ret = tcpd.wait_for_packets(count=1, timeout=3)
            self.assertEquals(1, len(ret))
        finally:
            tcpd.stop_capture()

    def test_timeout_blocking(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
        lo_iface = out.split()[0].rstrip()

        try:
            tcpd.start_capture(interface=lo_iface, count=1,
                               pcap_filter=PCAP_And(
                                   [
                                       PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                       PCAP_Port(6015, proto='tcp', source=True),
                                       PCAP_Port(6055, proto='tcp', dest=True)
                                   ]
                               ), blocking=True, timeout=3)
        except SubprocessTimeoutException:
            pass
        else:
            self.assertTrue(False, "Blocking tcpdump call should have timed out since no packets were sent")
        finally:
            tcpd.stop_capture()

    def test_callback(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        try:
            out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
            lo_iface = out.split()[0].rstrip()

            LinuxCLI().rm('tmp.file')

            tcpd.start_capture(interface=lo_iface, count=3,
                               pcap_filter=PCAP_And(
                                   [
                                       PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                       PCAP_Port(6015, proto='tcp', source=True),
                                       PCAP_Port(6055, proto='tcp', dest=True)
                                   ]
                               ),
                               callback=packet_callback, callback_args=('tmp.file',),
                               save_dump_file=True, save_dump_filename='tcp.callback.out')

            tcps.start_send(interface=lo_iface, packet_type='tcp', count=3, source_ip='127.0.0.1',
                            dest_ip='127.0.0.1', dest_port=6055, source_port=6015)

            ret = tcpd.wait_for_packets(count=3)
            tcpd.stop_capture()
            time.sleep(2)

            self.assertEquals(3, len(ret))

            self.assertTrue(LinuxCLI().exists('tmp.file'))
            file_str = LinuxCLI().read_from_file('tmp.file')
            LinuxCLI().rm('tmp.file')

            self.assertEquals(3, file_str.count('PACKET { time'))
        finally:
            tcpd.stop_capture()

    def test_early_stop(self):
        tcpd = TCPDump()
        tcps = TCPSender()

        try:
            out = LinuxCLI().cmd('ip l | grep "LOOPBACK" | cut -f 2 -d " "| cut -f 1 -d ":"').stdout
            lo_iface = out.split()[0].rstrip()

            tcpd.start_capture(interface=lo_iface, count=0,
                               pcap_filter=PCAP_And(
                                   [
                                       PCAP_Host('localhost', proto='ip', source=True, dest=True),
                                       PCAP_Port(6015, proto='tcp', source=True),
                                       PCAP_Port(6055, proto='tcp', dest=True)
                                   ]
                               ))

            tcps.start_send(interface=lo_iface, packet_type='tcp', count=5, source_ip='127.0.0.1',
                            dest_ip='127.0.0.1', dest_port=6055, source_port=6015)

            ret = tcpd.wait_for_packets(count=3, timeout=3)
            self.assertEqual(3, len(ret))
            ret = tcpd.wait_for_packets(count=1, timeout=3)
            self.assertEqual(1, len(ret))

            proc = tcpd.stop_capture()

            ret = tcpd.wait_for_packets(count=1, timeout=3)
            self.assertEqual(1, len(ret))

            self.assertTrue(not proc.is_alive())
        finally:
            tcpd.stop_capture()

    def tearDown(self):
        time.sleep(2)
        LinuxCLI().rm('tcp.callback.out')
        LinuxCLI().rm('tcp.out')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(TCPDumpTest)
