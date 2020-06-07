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

"""
import os.path
import stat
import yaml
import xml.etree.ElementTree


class Config(object):
    """ handle to captive portal config (/usr/local/etc/captiveportal.yaml)
    """
    _cnf_filename = "/usr/local/etc/captiveportal.yaml"

    def __init__(self):
        """ consctruct new config object
        """
        self.last_updated = 0
        self._zones = None
        self._update()

    def _update(self):
        """ check if config is changed and (re)load
        """
        mod_time = os.stat(self._cnf_filename)[stat.ST_MTIME]
        if os.path.exists(self._cnf_filename) and self.last_updated != mod_time:
            confFile = open(self._cnf_filename, 'r')
            if confFile:            
                confYaml = yaml.load(confFile, Loader=yaml.BaseLoader)
                self._process_yaml(confYaml)
                self.last_updated = mod_time

    def _process_yaml(self, confYaml):
        """ return list of configured zones
            :return: dictionary index by zoneid, containing dictionaries with zone properties
        """
        self._zones = dict()
        if 'zones' in confYaml:
            for zone in confYaml['zones']:
                self._zones[zone['id']] = zone 
                if 'macAccess' in zone:
                    passMacs = dict()
                    blockMacs = dict()
                    for mac in zone['macAccess']: 
                        if mac['action'] == 'pass':
                            passMacs[mac['mac']] = mac
                        elif mac['action'] == 'block':
                            blockMacs[mac['mac']] = mac      
                    zone['passMacAccess'] = passMacs
                    zone['blockMacAccess'] = blockMacs
                if 'ipAccess' in zone:
                    ips = dict()
                    for ip in zone['ipAccess']: 
                        ips[ip['ip']] = ip  
                    zone['ipAccess'] = ips                                                

    def get_zones(self):
        """ return list of configured zones
            :return: dictionary index by zoneid, containing dictionaries with zone properties
        """
        self._update()
        if self._zones is not None:
            return self._zones           
                
        return dict()

    def get_zone(self, zoneid):
        zones = self.get_zones()
        if zoneid in zones:
            return zones[zoneid]
        return None

    def fetch_template_data(self, zoneid):
        zone = self.get_zone(zoneid)
        if zone is not None and 'template' in zone:
            return zone['template']
        return None    
            

class OPNsenseConfig(object):
    """ Read configuration data from config.xml
    """
    def __init__(self):
        self.rootNode = None
        self.load_config()

    def load_config(self):
        """ load config.xml
        """
        tree = xml.etree.ElementTree.parse('/conf/config.xml')
        self.rootNode = tree.getroot()

    def get_template(self, fileid):
        """ fetch template content from config.xml
            :param fileid: internal fileid (field in template node)
            :return: string, bse64 encoded data or None if not found
        """
        templates = self.rootNode.findall("./OPNsense/captiveportal/templates/template")
        if templates is not None:
            for template in templates:
                if template.find('fileid') is not None and template.find('content') is not None:
                    if template.find('fileid').text == fileid:
                        return template.find('content').text

        return None
