#!/usr/local/bin/python3

"""
    Copyright (c) 2015-2019 Ad Schellevis <ad@opnsense.org>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    --------------------------------------------------------------------------------------
    update captive portal statistics
"""
import sys
import time
import syslog
import traceback
import subprocess
sys.path.insert(0, "/usr/local/opnsense/site-python")
from lib import Config
from lib.db import DB
from lib.arp import ARP
from lib.ipfw import IPFW
from lib.daemonize import Daemonize
from sqlite3_helper import check_and_repair


class CPBackgroundProcess(object):
    """ background process helper class
    """
    def __init__(self):
        # open syslog and notice startup
        syslog.openlog('captiveportal', logoption=syslog.LOG_DAEMON, facility=syslog.LOG_LOCAL4)
        syslog.syslog(syslog.LOG_NOTICE, 'starting captiveportal background process')
        # handles to ipfw, arp the config and the internal administration
        self.ipfw = IPFW()
        self.arp = ARP()
        self.cnf = Config()
        self.db = DB()
        self._conf_zone_info = self.cnf.get_zones()

    def list_zone_ids(self):
        """ return zone numbers
        """
        return self._conf_zone_info.keys()

    def initialize_fixed(self):
        """ initialize fixed ip / hosts per zone
        """
        for zoneid, zone in self._conf_zone_info.items():
            if 'passMacAccess' in zone:
                for mac in zone['passMacAccess']:    
                    sessions = self.db.sessions_per_address(zoneid, mac_address=mac)              
                    sessions_deleted = 0
                    for session in sessions:
                        if session['authenticated_via'] not in ('---ip---', '---mac---'):
                            sessions_deleted += 1
                            self.db.del_client(zoneid, session['sessionId'])
                    if sessions_deleted == len(sessions) or len(sessions) == 0:
                        # when there's no session active, add a new one
                        # (only administrative, the sync process will add it if neccesary)
                        self.db.add_client(zoneid, "---mac---", "", "", mac)
                            
            if 'ipAccess' in zone:
                for ip in zone['ipAccess']:    
                    sessions = self.db.sessions_per_address(zoneid, ip_address=ip)              
                    sessions_deleted = 0
                    for session in sessions:
                        if session['authenticated_via'] not in ('---ip---', '---mac---'):
                            sessions_deleted += 1
                            self.db.del_client(zoneid, session['sessionId'])
                    if sessions_deleted == len(sessions) or len(sessions) == 0:
                        # when there's no session active, add a new one
                        # (only administrative, the sync process will add it if neccesary)
                        self.db.add_client(zoneid, "---ip---", "", ip, "")

            # cleanup removed static sessions
            for dbclient in self.db.list_clients(zoneid):
                if dbclient['authenticated_via'] == '---ip---' \
                        and dbclient['ipAddress'] not in zone['ipAccess']:
                        self.ipfw.delete(zoneid, dbclient['ipAddress'])
                        self.db.del_client(zoneid, dbclient['sessionId'])
                elif dbclient['authenticated_via'] == '---mac---' \
                        and dbclient['macAddress'] not in zone['passMacAccess']:
                        if dbclient['ipAddress'] != '':
                            self.ipfw.delete(zoneid, dbclient['ipAddress'])
                        self.db.del_client(zoneid, dbclient['sessionId'])

    def add_traffic_shapper(self, config, ip_address):
        if 'shaperUpload' in config:
            self.ipfw.add_traffic_shapper(config['shaperUpload']['type'], config['shaperUpload']['number'], 'out', ip_address)
        if 'shaperDownload' in config:
            self.ipfw.add_traffic_shapper(config['shaperDownload']['type'], config['shaperDownload']['number'], 'in', ip_address)

    def add_traffic_shapper_by_ip(self, zoneid, ip_address):
        if ip_address in self._conf_zone_info[zoneid]['ipAccess']:
            ip_config = self._conf_zone_info[zoneid]['ipAccess'][ip_address]
            self.add_traffic_shapper(ip_config, ip_address)

    def add_traffic_shapper_by_mac(self, zoneid, mac_address, ip_address):
        if mac_address in self._conf_zone_info[zoneid]['passMacAccess']:
            mac_config = self._conf_zone_info[zoneid]['passMacAccess'][mac_address]
            self.add_traffic_shapper(mac_config, ip_address)

    def sync_zone(self, zoneid):
        """ Synchronize captiveportal zone.
            Handles timeouts and administrative changes to this zones sessions
        """
        if zoneid in self._conf_zone_info:
            # fetch data for this zone
            registered_addresses = self.ipfw.list_table(zoneid)
            registered_addr_accounting = self.ipfw.list_accounting_info()
            expected_clients = self.db.list_clients(zoneid)
            concurrent_users = self.db.find_concurrent_user_sessions(zoneid)

            # handle connected clients, timeouts, address changes, etc.
            for db_client in expected_clients:
                # fetch ip address (or network) from database
                cpnet = db_client['ipAddress'].strip()

                # there are different reasons why a session should be removed, check for all reasons and
                # use the same method for the actual removal
                drop_session_reason = None

                # session cleanups, only for users not for static hosts/ranges.
                if db_client['authenticated_via'] not in ('---ip---', '---mac---'):
                    # check if hardtimeout is set and overrun for this session
                    if 'hardtimeout' in zone and str(zone['hardtimeout']).isdigit():
                        # hardtimeout should be set and we should have collected some session data from the client
                        if int(zone['hardtimeout']) > 0 and float(db_client['startTime']) > 0:
                            if (time.time() - float(db_client['startTime'])) / 60 > int(zone['hardtimeout']):
                                drop_session_reason = "session %s hit hardtimeout" % db_client['sessionId']

                    # check if idletimeout is set and overrun for this session
                    if 'idletimeout' in zone and str(zone['idletimeout']).isdigit():
                        # idletimeout should be set and we should have collected some session data from the client
                        if int(zone['idletimeout']) > 0 and float(db_client['last_accessed']) > 0:
                            if (time.time() - float(db_client['last_accessed'])) / 60 > int(zone['idletimeout']):
                                drop_session_reason = "session %s hit idletimeout" % db_client['sessionId']

                    # cleanup concurrent users
                    if 'concurrentlogins' in zone and int(zone['concurrentlogins']) == 0:
                        if db_client['sessionId'] in concurrent_users:
                            drop_session_reason = "remove concurrent session %s" % db_client['sessionId']

                    # if mac address changes, drop session. it's not the same client
                    current_arp = self.arp.get_by_ipaddress(cpnet)
                    if current_arp is not None and current_arp['mac'] != db_client['macAddress']:
                        drop_session_reason = "mac address changed for session %s" % db_client['sessionId']

                    # session accounting
                    if db_client['acc_session_timeout'] is not None \
                            and type(db_client['acc_session_timeout']) in (int, float) \
                            and time.time() - float(db_client['startTime']) > db_client['acc_session_timeout']:
                            drop_session_reason = "accounting limit reached for session %s" % db_client['sessionId']
                elif db_client['authenticated_via'] == '---mac---':
                    # detect mac changes
                    current_ip = self.arp.get_address_by_mac(db_client['macAddress'])
                    if current_ip is not None and current_ip != cpnet:
                        if cpnet != '':
                            # remove old ip
                            self.ipfw.delete(zoneid, cpnet)
                        self.db.update_client_ip(zoneid, db_client['sessionId'], current_ip)
                        self.ipfw.add_to_table(zoneid, current_ip)
                        self.add_traffic_shapper_by_mac(zoneid, db_client['macAddress'], current_ip)

                # check session, if it should be active, validate its properties
                if drop_session_reason is None:
                    # registered client, but not active or missing accounting according to ipfw (after reboot)
                    if cpnet != '' and (cpnet not in registered_addresses or cpnet not in registered_addr_accounting):
                        self.ipfw.add_to_table(zoneid, cpnet)
                        if db_client['authenticated_via'] == '---mac---':
                            self.add_traffic_shapper_by_mac(zoneid, db_client['macAddress'], cpnet)
                        else:
                            self.add_traffic_shapper_by_ip(zoneid, cpnet)

                else:
                    # remove session
                    syslog.syslog(syslog.LOG_NOTICE, drop_session_reason)
                    self.ipfw.delete(zoneid, cpnet)
                    self.db.del_client(zoneid, db_client['sessionId'])

            # if there are addresses/networks in the underlying ipfw table which are not in our administration,
            # remove them from ipfw.
            for registered_address in registered_addresses:
                address_active = False
                for db_client in expected_clients:
                    if registered_address == db_client['ipAddress']:
                        address_active = True
                        break
                if not address_active:
                    self.ipfw.delete(zoneid, registered_address)


def main():
    """ Background process loop, runs as backend daemon for all zones. only one should be active at all times.
        The main job of this procedure is to sync the administration with the actual situation in the ipfw firewall.
    """
    # perform integrity check and repair database if needed
    check_and_repair('/var/captiveportal/captiveportal.sqlite')

    last_cleanup_timestamp = 0
    bgprocess = CPBackgroundProcess()
    bgprocess.initialize_fixed()

    while True:
        try:
            # open database
            bgprocess.db.open()

            # cleanup old settings, every 5 minutes
            if time.time() - last_cleanup_timestamp > 300:
                bgprocess.db.cleanup_sessions()
                last_cleanup_timestamp = time.time()

            # reload cached arp table contents
            bgprocess.arp.reload()

            # update accounting info, for all zones
            bgprocess.db.update_accounting_info(bgprocess.ipfw.list_accounting_info())

            # process sessions per zone
            for zoneid in bgprocess.list_zone_ids():
                bgprocess.sync_zone(zoneid)

            # close the database handle while waiting for the next poll
            bgprocess.db.close()

            # process accounting messages (uses php script, for reuse of Auth classes)
            try:
                subprocess.run(
                    ['/usr/local/opnsense/scripts/OPNsense/CaptivePortal/process_accounting_messages.php'],
                    capture_output=True
                )
            except OSError:
                # if accounting script crashes don't exit backgroung process
                pass

            # sleep
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except SystemExit:
            break
        except:
            syslog.syslog(syslog.LOG_ERR, traceback.format_exc())
            print(traceback.format_exc())
            break

# startup
if len(sys.argv) > 1 and sys.argv[1].strip().lower() == 'run':
    main()
else:
    daemon = Daemonize(app=__file__.split('/')[-1].split('.py')[0], pid='/var/run/captiveportal.db.pid', action=main)
    daemon.start()
