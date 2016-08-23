import logging
import random
import wishful_upis as upis
import wishful_framework as wishful_module
import subprocess
from wishful_framework.classes import exceptions
import inspect
import fcntl, socket, struct
import netifaces as ni
from scapy.all import *
from datetime import date, datetime
import os

__author__ = "Piotr Gawlowicz, Mikolaj Chwalisz, Zubow"
__copyright__ = "Copyright (c) 2015, Technische Universität Berlin"
__version__ = "0.1.0"
__email__ = "{gawlowicz, chwalisz, zubow}@tkn.tu-berlin.de"

@wishful_module.build_module
class WifiModule(wishful_module.AgentModule):
    def __init__(self):
        super(WifiModule, self).__init__()
        self.log = logging.getLogger('wifi_module.main')
        self.interface = "wlan0"
        self.wlan_interface = "wlan0"
        self.channel = 1
        self.power = 1
        self.modulation_rate = 1

    @wishful_module.bind_function(upis.radio.set_power)
    def set_power(self, power_dBm):

        self.log.info('setting set_power(): %s->%s' % (str(self.wlan_interface), str(power_dBm)))

        cmd_str = 'iw dev ' + self.wlan_interface + ' set txpower fixed ' + str(power_dBm) + 'dbm'

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        self.power = power_dBm


    @wishful_module.bind_function(upis.radio.get_power)
    def get_power(self):
        self.log.debug("WIFI Module gets power of interface: {}".format(self.interface))
        return self.power


    @wishful_module.bind_function(upis.wifi.radio.set_channel)
    def set_channel(self, channel):

        self.log.info('setting channel(): %s->%s' % (str(self.interface), str(channel)))

        cmd_str = 'sudo iwconfig ' + self.interface + ' channel ' + str(channel)

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        return True


    @wishful_module.bind_function(upis.wifi.radio.get_channel)
    def get_channel(self):
        self.log.debug("WIFI Module gets channel of interface: {}".format(self.interface))
        return self.channel

    @wishful_module.bind_function(upis.radio.set_modulation_rate)
    def set_modulation_rate(self, rate_Mbps):

        self.log.info('setting modulation rate(): %s->%s' % (str(self.wlan_interface), str(rate_Mbps)))

        cmd_str = 'iwconfig ' + self.wlan_interface + ' rate ' + str(rate_Mbps) + 'M' + ' fixed'

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        self.modulation_rate = rate_Mbps

    @wishful_module.bind_function(upis.wifi.net.set_hostapd_conf)
    def set_hostapd_conf(self, iface, file_path, channel, essid):
        self.log.debug("WIFI Module set hostapd configuratin file: {}".format(self.wlan_interface))

        from hostapdconf.parser import HostapdConf
        from hostapdconf import helpers as ha
        #read start configuration file
        conf = HostapdConf(file_path)
        #set wireless interface
        ha.set_iface(conf, iface)
        #set wireless channel
        ha.set_channel(conf, channel)
        #set ESSID
        ha.set_ssid(conf, essid)
        #write new configuraiton
        conf.write()

        return True

    @wishful_module.bind_function(upis.wifi.net.start_hostapd)
    def start_hostapd(self, file_path):
        self.log.info('start hostapd()')

        cmd_str = 'sudo hostapd -B ' + str(file_path)
        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
            #sp = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            #out, err = sp.communicate()
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        self.log.info('start hostapd() completed')

        return True

    @wishful_module.bind_function(upis.wifi.net.stop_hostapd)
    def stop_hostapd(self):
        self.log.info('stop hostapd()')

        cmd_str = 'ps aux | grep hostapd | wc -l'
        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        if (int(sout)>2):
            cmd_str = 'sudo killall -9 hostapd'
            try:
                [rcode, sout, serr] = self.run_command(cmd_str)
            except Exception as e:
                fname = inspect.currentframe().f_code.co_name
                self.log.fatal("An error occurred in %s: %s" % (fname, e))
                raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        self.log.info('stop hostapd() completed')

        return True

    @wishful_module.bind_function(upis.wifi.net.get_info_of_connected_devices)
    def get_info_of_connected_devices(self):
        '''
            Returns information about associated STAs for a node running in AP mode
            tbd: use Netlink API
        '''

        self.log.info("WIFI Module get info on associated clients on interface: {}".format(self.interface))

        try:
            [rcode, sout, serr] = self.run_command('iw dev ' + self.interface + ' station dump')

            # mac_addr -> stat_key -> list of (value, unit)
            res = {}
            sout_arr = sout.split("\n")

            for line in sout_arr:
                s = line.strip()
                if s == '':
                    continue
                if "Station" in s:
                    arr = s.split()
                    mac_addr = arr[1].strip()
                    res[mac_addr] = {}
                else:
                    arr = s.split(":")
                    key = arr[0].strip()
                    val = arr[1].strip()

                    arr2 = val.split()
                    val2 = arr2[0].strip()

                    if len(arr2) > 1:
                        unit = arr2[1].strip()
                    else:
                        unit = None

                    res[mac_addr][key] = (val2, unit)
            return res
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))


    @wishful_module.bind_function(upis.wifi.net.get_inactivity_time_of_connected_devices)
    def get_inactivity_time_of_connected_devices(self):
        return self.get_entry_of_connected_devices('inactive time')


    @wishful_module.bind_function(upis.wifi.net.get_avg_sigpower_of_connected_devices)
    def get_avg_sigpower_of_connected_devices(self):
        return self.get_entry_of_connected_devices('signal avg')


    @wishful_module.bind_function(upis.wifi.net.get_sigpower_of_connected_devices)
    def get_sigpower_of_connected_devices(self):
        return self.get_entry_of_connected_devices('signal')


    @wishful_module.bind_function(upis.wifi.net.get_tx_retries_of_connected_devices)
    def get_tx_retries_of_connected_devices(self):
        return self.get_entry_of_connected_devices('tx retries')


    @wishful_module.bind_function(upis.wifi.net.get_tx_packets_of_connected_devices)
    def get_tx_packets_of_connected_devices(self):
        return self.get_entry_of_connected_devices('tx packets')


    @wishful_module.bind_function(upis.wifi.net.get_tx_failed_of_connected_devices)
    def get_tx_failed_of_connected_devices(self):
        return self.get_entry_of_connected_devices('tx failed')


    @wishful_module.bind_function(upis.wifi.net.get_tx_bytes_of_connected_devices)
    def get_tx_bytes_of_connected_devices(self):
        return self.get_entry_of_connected_devices('tx bytes')


    @wishful_module.bind_function(upis.wifi.net.get_tx_bitrate_of_connected_devices)
    def get_tx_bitrate_of_connected_devices(self):
        return self.get_entry_of_connected_devices('tx bitrate')


    @wishful_module.bind_function(upis.wifi.net.get_rx_bytes_of_connected_devices)
    def get_rx_bytes_of_connected_devices(self):
        return self.get_entry_of_connected_devices('rx bytes')


    @wishful_module.bind_function(upis.wifi.net.get_rx_packets_of_connected_devices)
    def get_rx_packets_of_connected_devices(self):
        return self.get_entry_of_connected_devices('rx packets')


    @wishful_module.bind_function(upis.wifi.net.get_authorized_connected_device)
    def get_authorized_connected_device(self):
        return self.get_entry_of_connected_devices('authorized')


    @wishful_module.bind_function(upis.wifi.net.get_authenticated_connected_device)
    def get_authenticated_connected_device(self):
        return self.get_entry_of_connected_devices('authenticated')


    @wishful_module.bind_function(upis.wifi.net.get_used_preamble_connected_device)
    def get_used_preamble_connected_device(self):
        return self.get_entry_of_connected_devices('preamble')


    @wishful_module.bind_function(upis.wifi.net.get_mfp_connected_device)
    def get_mfp_connected_device(self):
        return self.get_entry_of_connected_devices('MFP')


    @wishful_module.bind_function(upis.wifi.net.get_wmm_wme_connected_device)
    def get_wmm_wme_connected_device(self):
        return self.get_entry_of_connected_devices('WMM/WME')


    @wishful_module.bind_function(upis.wifi.net.get_tdls_peer_connected_device)
    def get_tdls_peer_connected_device(self):
        return self.get_entry_of_connected_devices('TDLS peer')


    @wishful_module.bind_function(upis.wifi.net.connect_to_network)
    def connect_to_network(self, iface, ssid):

        self.log.info('connecting via to AP with SSID: %s->%s' % (str(self.wlan_interface), str(ssid)))

        cmd_str = 'sudo iwconfig ' + str(iface) + ' essid ' + str(ssid)

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        return True

    @wishful_module.bind_function(upis.wifi.net.network_dump)
    def network_dump(self, iface):

        self.log.info('dump_network on interface %s' % (str(iface)))

        cmd_str = 'sudo iw dev ' + str(iface) + ' link'

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        return sout

    @wishful_module.bind_function(upis.net.set_ip_address)
    def set_ip_address(self, iface, ip_address):

        self.log.info('setting ip address(): %s->%s' % (str(self.wlan_interface), str(ip_address)))

        cmd_str = 'sudo ifconfig ' + str(iface) + ' ' + str(ip_address)

        try:
            [rcode, sout, serr] = self.run_command(cmd_str)
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

        return True


    @wishful_module.bind_function(upis.net.gen_layer2_traffic)
    def gen_layer2_traffic(self, iface, num_packets, pinter, max_phy_broadcast_rate_mbps, **kwargs):

        self.log.info('gen_layer2_traffic ... here 802.11()')

        ipdst = kwargs.get('ipdst')
        ipsrc = kwargs.get('ipsrc')

        # get my MAC HW address
        myMacAddr = self.getHwAddr({'iface': iface})
        dstMacAddr = 'ff:ff:ff:ff:ff:ff'

        if pinter is not None:
            # generate with some packet interval
            if num_packets > 255:
                num_packets = 255

            data = RadioTap() / Dot11(type=2, subtype=0, addr1=dstMacAddr, addr2=myMacAddr, addr3=myMacAddr) / LLC() / SNAP() / IP(dst=ipdst, src=ipsrc, ttl=(1,num_packets))
            sendp(data, iface=iface, inter=pinter)

            return 1.0 / pinter
        else:
            assert max_phy_broadcast_rate_mbps is not None

            use_tcpreplay = kwargs.get('use_tcpreplay')

            # craft packet to be transmitted
            payload = 'Z' * ipPayloadSize
            data = RadioTap() / Dot11(type=2, subtype=0, addr1=dstMacAddr, addr2=myMacAddr, addr3=myMacAddr) \
                   / LLC() / SNAP() / IP(dst=ipdst, src=ipsrc) / payload

            # send 10 packets backlogged
            now = datetime.now()
            if use_tcpreplay:
                # use tcprelay
                sendpfast(data, iface=iface, mbps=phyBroadcastMbps, loop=num_packets, file_cache=True)
            else:
                piter = (len(data) * 8) / (phyBroadcastMbps * 1e6)
                sendp(data, iface=iface, loop=1, inter=piter, realtime=True, count=num_packets, verbose=0)

            delta = datetime.now()-now
            # calc achieved transmit data rate
            tx_frame_rate = 1.0 / ((delta.seconds + delta.microseconds / 1000000.0) / num_packets)

            self.log.info('gen80211L2LinkProbing(): tx_frame_rate=%d' % int(tx_frame_rate))

            return tx_frame_rate


    @wishful_module.bind_function(upis.net.sniff_layer2_traffic)
    def sniff_layer2_traffic(self, iface, sniff_timeout, **kwargs):

        self.log.info('sniff layer 2 traffic ... here 802.11')

        # some additional filtering ...todo!!!!!!!
        ipdst = kwargs.get('ipdst')
        ipsrc = kwargs.get('ipsrc')

        rx_pkts = {}
        rx_pkts['res'] = 0

        def ip_monitor_callback(pkt):
            if IP in pkt and pkt[IP].src == ipsrc and pkt[IP].dst == ipdst:
                rx_pkts['res'] = rx_pkts['res'] + 1
                #return pkt.sprintf("{IP:%IP.src% -> %IP.dst% -> %IP.ttl%\n}")

        sniff(iface=iface, prn=ip_monitor_callback, timeout=sniff_timeout)

        numRxPkts = rx_pkts['res']
        self.log.info('sniff80211L2LinkProbing(): rxpackets= %d' % numRxPkts)
        return numRxPkts


    @wishful_module.bind_function(upis.net.inject_frame)
    def inject_frame(self, iface, frame, is_layer_2_packet, tx_count=1, pkt_interval=1):
        self.log.debug("Inject frame".format())

        if is_layer_2_packet:
            sendp(frame, iface=iface, inter=pkt_interval, realtime=True, count=tx_count, verbose=0)
        else:
            send(frame, iface=iface, inter=pkt_interval, realtime=True, count=tx_count, verbose=0)

        return True


    @wishful_module.bind_function(upis.wifi.net.disconnect_device)
    def disconnect_device(self, iface, sta_mac_addr):
        """
            Send a disaccociation request frame to a client STA associated with this AP.
            tbd: what is -p ?? Please simplify
        """

        exec_file = str(os.path.join(self.getPlatformPathHandover())) + '/hostapd_cli'
        args = '-p /tmp/hostapd-' + iface + ' disassociate'

        command = exec_file + ' ' + args + ' ' + sta_mac_addr
        self.log.debug('Disassociate STA %s on iface %s' % (sta_mac_addr, iface))
        self.log.debug('exe: %s' % command)

        try:
            [rcode, sout, serr] = self.run_command(command)
            return sout
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))


    @wishful_module.bind_function(upis.wifi.net.remove_device_from_blacklist)
    def remove_device_from_blacklist(self, iface, sta_mac_addr):
        """
            Unblacklist a given STA in the AP, i.e. the STA is able to associate with this AP afterwards.
            tbd: what is -p ?? Please simplify
        """

        exec_file = str(os.path.join(self.getPlatformPathHandover())) + '/hostapd_cli'
        args = '-p /tmp/hostapd-' + iface + ' unblacklist_sta'

        command = exec_file + ' ' + args + ' ' + sta_mac_addr
        self.log.debug('exe: %s' % command)
        self.log.debug('Unblacklist node %s on iface %s' % (sta_mac_addr, iface))

        try:
            [rcode, sout, serr] = self.run_command(command)
            return sout
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))


    @wishful_module.bind_function(upis.wifi.net.add_device_to_blacklist)
    def add_device_to_blacklist(self, iface, sta_mac_addr):
        """
            Blacklist a given STA in the AP, i.e. any request for association by the STA will be ignored by the AP.
            tbd: what is -p ?? Please simplify
        """

        exec_file = str(os.path.join(self.getPlatformPathHandover())) + '/hostapd_cli'
        args = '-p /tmp/hostapd-' + iface + ' blacklist_sta'

        command = exec_file + ' ' + args + ' ' + sta_mac_addr
        self.log.debug('Blacklist node %s on iface %s' % (sta_mac_addr, iface))
        self.log.debug('exec %s' % command)

        try:
            [rcode, sout, serr] = self.run_command(command)
            return sout
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))


    @wishful_module.bind_function(upis.wifi.net.register_new_device)
    def register_new_device(self, iface, sta_mac_addr):
        """
            Register a new STA within the AP, i.e. afterwards the STA is able to exchange data frames.
            tbd: consider client capabilities
        """

        self.log.debug('Add new STA %s on iface %s' % (sta_mac_addr, iface))

        exec_file = str(os.path.join(self.getPlatformPathHandover())) + '/hostapd_cli'

        self.log.debug('exec path: %s' % exec_file)

        try:
            [rcode, sout, serr] = self.run_command(exec_file + " -p /tmp/hostapd-" + iface + " new_sta " + sta_mac_addr)
            return sout
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))


    @wishful_module.bind_function(upis.wifi.net.trigger_channel_switch_in_device)
    def trigger_channel_switch_in_device(self, iface, sta_mac_addr, target_channel, serving_channel, **kwargs):
        """
            Transmit Channel Switch Announcement (CSA) beacon to the given STA.
        """

        bssid = kwargs.get('bssid')
        self.log.debug('Sending CSA to %s on iface %s with BSSID %s switch STA to channel %s' % (sta_mac_addr, iface, bssid, str(target_channel)))

        # tbd: clean up this mess
        beacon = RadioTap() / Dot11(type=0, subtype=8, addr1=sta_mac_addr, addr2=bssid, addr3=bssid) / binascii.unhexlify(
                '3bc0904f00000000640001000005424947415001088c129824b048606c0301'+ hex(
                    serving_channel).replace("0x", "")+'050400020000070c44452024081464051a84031a2d1a0c001bffff0000000000000000000001000000000000000000003d162c0004000000000000000000000000000000000000007f080000000000000040dd180050f2020101800003a4000027a4000042435d0062322e00dd06aaaaaa3f4325dd14aaaaaa8020544b4e2d4c6f57532d53797374656ddd06aaaaaa215a01250300' + hex(
                    target_channel).replace("0x", "") + '00')

        # tbd: do we really need this
        BEACON_ARQ = 3
        for ii in range(BEACON_ARQ):
            # repetitive transmission
            sendp(beacon, iface=iface)
        return True


    #################################################
    # Helper functions
    #################################################

    def get_entry_of_connected_devices(self, key):

        try:
            res = self.get_info_of_connected_devices()

            rv = {}
            for mac_addr in res:
                value = res[mac_addr][key]
                self.log.info('%s -> %s' % (mac_addr, value))
                rv[mac_addr] = value

            # dict of mac_addr -> value
            return rv
        except Exception as e:
            fname = inspect.currentframe().f_code.co_name
            self.log.fatal("An error occurred in %s: %s" % (fname, e))
            raise exceptions.UPIFunctionExecutionFailedException(func_name=fname, err_msg=str(e))

    def run_command(self, command):
        '''
            Method to start the shell commands and get the output as iterater object
        '''

        sp = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = sp.communicate()

        if False:
            if out:
                self.log.debug("standard output of subprocess:")
                self.log.debug(out)
            if err:
                self.log.debug("standard error of subprocess:")
                self.log.debug(err)

        if err:
            raise Exception("An error occurred in Dot80211Linux: %s" % err)

        return [sp.returncode, out.decode("utf-8"), err.decode("utf-8")]

    def run_timeout_command(self, command, timeout):
        """
            Call shell-command and either return its output or kill it
            if it doesn't normally exit within timeout seconds and return None
        """
        cmd = command.split(" ")
        start = datetime.datetime.now()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() is None:
            time.sleep(0.1)
            now = datetime.datetime.now()
            if (now - start).seconds > timeout:
                os.kill(process.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
                return process.stdout.read()
        return process.stdout.read()
