<?php
/**
 *    Copyright (C) 2015 Deciso B.V.
 *
 *    All rights reserved.
 *
 *    Redistribution and use in source and binary forms, with or without
 *    modification, are permitted provided that the following conditions are met:
 *
 *    1. Redistributions of source code must retain the above copyright notice,
 *       this list of conditions and the following disclaimer.
 *
 *    2. Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *
 *    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 *    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 *    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 *    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *    POSSIBILITY OF SUCH DAMAGE.
 *
 */
namespace OPNsense\CaptivePortal\Api;

use \OPNsense\Base\ApiControllerBase;
use \OPNsense\Core\Backend;
use \OPNsense\Core\Config;
use \OPNsense\CaptivePortal\CaptivePortal;
use \OPNsense\Base\UIModelGrid;
 
/**
 * Class HostAccessController Handles pass-through related API actions for Captive Portal
 * @package OPNsense\TrafficShaper
 */
class HostaccessController extends ApiControllerBase
{
    /**
     * validate and save model after update or insertion.
     * Use the reference node and tag to rename validation output for a specific node to a new offset, which makes
     * it easier to reference specific uuids without having to use them in the frontend descriptions.
     * @param $mdl model reference
     * @param $node reference node, to use as relative offset
     * @param $reference reference for validation output, used to rename the validation output keys
     * @return array result / validation output
     */
    private function save($mdl, $node = null, $reference = null)
    {
        $result = array("result"=>"failed","validations" => array());
        // perform validation
        $valMsgs = $mdl->performValidation();
        foreach ($valMsgs as $field => $msg) {
            // replace absolute path to attribute for relative one at uuid.
            if ($node != null) {
                $fieldnm = str_replace($node->__reference, $reference, $msg->getField());
                $result["validations"][$fieldnm] = $msg->getMessage();
            } else {
                $result["validations"][$msg->getField()] = $msg->getMessage();
            }
        }

        // serialize model to config and save when there are no validation errors
        if (count($result['validations']) == 0) {
            // save config if validated correctly
            $mdl->serializeToConfig();
            Config::getInstance()->save();

            if ($this->reloadConfig($mdl)) {
                $result = array("result" => "saved");
            }
        }

        return $result;
    }

    /**
     * reload captive portal template config
     * must be called after config is saved
     * @param $mdlCP Captive portal model reference
     */
    private function reloadConfig($mdlCP)
    {
        $backend = new Backend();
    
        // generate captive portal config
        $bckresult = trim($backend->configdRun('template reload OPNsense/Captiveportal'));
        if ($bckresult == "OK") {
            if ($mdlCP->isEnabled()) {
                $bckresult = trim($backend->configdRun("captiveportal restart"));
                if ($bckresult == "OK") {
                    return true;
                }
            }
        } 

        return false;
    }    

    /**
     * retrieve Mac rules or return defaults
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array
     */
    public function getMacRuleAction($zoneid = 0, $uuid = null)
    {
        $mdlCP = new CaptivePortal();
        $cpZone = $mdlCP->getByZoneID($zoneid);
        if ($cpZone != null) {
            if ($uuid != null) {
                $node = $cpZone->macAccess->macRule->{$uuid};
                if ($node != null) {
                    // return node
                    return array("macRule" => $node->getNodes());
                }
            } else {
                // generate new node, but don't save to disc
                $node = $cpZone->macAccess->macRule->add();
                return array("macRule" => $node->getNodes());
            }
        }
        return array();
    }

    /**
     * update Mac with given rule
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array
     */
    public function setMacRuleAction($zoneid = 0, $uuid)
    {
        if ($this->request->isPost() && $this->request->hasPost("macRule") && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                $node = $cpZone->macAccess->macRule->{$uuid};
                if ($node != null) {
                    $macRule = $this->request->getPost("macRule");
                    // If rule is to block mac access there is no need for traffic shapping
                    if (array_key_exists('action', $macRule) && $macRule['action'] == "block") {
                        $macRule['shaperDownload'] = '';
                        $macRule['shaperUpload'] = '';
                    }    
                    $node->setNodes($macRule);
                    return $this->save($mdlCP, $node, "macRule");
                }
            }
        }
        return array("result"=>"failed");
    }

    /**
     * add new Mac rule and set with attributes from post
     * @param int $zoneid zone number
     * @return array
     */
    public function addMacRuleAction($zoneid = 0)
    {
        $result = array("result"=>"failed");
        if ($this->request->isPost() && $this->request->hasPost("macRule")) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {     
                $macRule = $this->request->getPost("macRule");
                // If rule is to block mac access there is no need for traffic shapping
                if (array_key_exists('action', $macRule) && $macRule['action'] == "block") {
                    $macRule['shaperDownload'] = '';
                    $macRule['shaperUpload'] = '';
                }
                $node = $cpZone->macAccess->macRule->Add();
                $node->setNodes($macRule);
                return $this->save($mdlCP, $node, "macRule");
            }
        }
        return $result;
    }

    /**
     * delete Mac rule by uuid
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array status
     */
    public function delMacRuleAction($zoneid = 0, $uuid)
    {
        $result = array("result"=>"failed");
        if ($this->request->isPost() && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                if ($cpZone->macAccess->macRule->del($uuid)) {
                    // if item is removed, serialize to config and save
                    $mdlCP->serializeToConfig();
                    Config::getInstance()->save();
                    if ($this->reloadConfig($mdlCP)) {
                        $result['result'] = 'deleted';
                    }    
                } else {
                    $result['result'] = 'not found';
                }
            }
        }
        return $result;
    }

    /**
     * toggle Mac rule by uuid (enable/disable)
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @param $enabled desired state enabled(1)/disabled(1), leave empty for toggle
     * @return array status
     */
    public function toggleMacRuleAction($zoneid = 0, $uuid, $enabled = null)
    {

        $result = array("result" => "failed");
        if ($this->request->isPost() && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                $node = $cpZone->macAccess->macRule->{$uuid};
                if ($node != null) {
                    if ($enabled == "0" || $enabled == "1") {
                        $node->enabled = (string)$enabled;
                    } elseif ((string)$node->enabled == "1") {
                        $node->enabled = "0";
                    } else {
                        $node->enabled = "1";
                    }
                    $result['result'] = $node->enabled;
                    // if item has toggled, serialize to config and save
                    $mdlCP->serializeToConfig();
                    Config::getInstance()->save();
                    $this->reloadConfig($mdlCP);
                }
            }
        }
        return $result;
    }

    /**
     * search captive portal Mac rules
     * @param int $zoneid zone number
     * @return array
     */
    public function searchMacRulesAction($zoneid = 0)
    {
        $mdlCP = new CaptivePortal();
        $cpZone = $mdlCP->getByZoneID($zoneid);
        if ($cpZone != null) {
            $grid = new UIModelGrid($cpZone->macAccess->macRule);
            return $grid->fetchBindRequest(
                $this->request,
                array("enabled", "action", "mac", "description", "shaperUpload", "shaperDownload"),
                "description"
            );
        } else {
            // illegal zone, return empty response
            return array();
        }
    }

    /**
     * retrieve Ip rules or return defaults
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array
     */
    public function getIpRuleAction($zoneid = 0, $uuid = null)
    {
        $mdlCP = new CaptivePortal();
        $cpZone = $mdlCP->getByZoneID($zoneid);
        if ($cpZone != null) {
            if ($uuid != null) {
                $node = $cpZone->ipAccess->ipRule->{$uuid};
                if ($node != null) {
                    // return node
                    return array("ipRule" => $node->getNodes());
                }
            } else {
                // generate new node, but don't save to disc
                $node = $cpZone->ipAccess->ipRule->add();
                return array("ipRule" => $node->getNodes());
            }
        }
        return array();
    }

    /**
     * update Ip with given rule
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array
     */
    public function setIpRuleAction($zoneid = 0, $uuid)
    {
        if ($this->request->isPost() && $this->request->hasPost("ipRule") && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                $node = $cpZone->ipAccess->ipRule->{$uuid};
                if ($node != null) {
                    $node->setNodes($this->request->getPost("ipRule"));
                    return $this->save($mdlCP, $node, "ipRule");
                }
            }
        }
        return array("result"=>"failed");
    }

    /**
     * add new Ip rule and set with attributes from post
     * @param int $zoneid zone number
     * @return array
     */
    public function addIpRuleAction($zoneid = 0)
    {
        $result = array("result"=>"failed");
        if ($this->request->isPost() && $this->request->hasPost("ipRule")) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                $node = $cpZone->ipAccess->ipRule->Add();
                $node->setNodes($this->request->getPost("ipRule"));
                return $this->save($mdlCP, $node, "ipRule");
            }
        }
        return $result;
    }

    /**
     * delete Ip rule by uuid
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @return array status
     */
    public function delIpRuleAction($zoneid = 0, $uuid)
    {
        $result = array("result"=>"failed");
        if ($this->request->isPost() && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                if ($cpZone->ipAccess->ipRule->del($uuid)) {
                    // if item is removed, serialize to config and save
                    $mdlCP->serializeToConfig();
                    Config::getInstance()->save();
                    if ($this->reloadConfig($mdlCP)) {
                        $result['result'] = 'deleted';
                    }
                } else {
                    $result['result'] = 'not found';
                }
            }
        }
        return $result;
    }

    /**
     * toggle Ip rule by uuid (enable/disable)
     * @param int $zoneid zone number
     * @param $uuid item unique id
     * @param $enabled desired state enabled(1)/disabled(1), leave empty for toggle
     * @return array status
     */
    public function toggleIpRuleAction($zoneid = 0, $uuid, $enabled = null)
    {

        $result = array("result" => "failed");
        if ($this->request->isPost() && $uuid != null) {
            $mdlCP = new CaptivePortal();
            $cpZone = $mdlCP->getByZoneID($zoneid);
            if ($cpZone != null) {
                $node = $cpZone->ipAccess->ipRule->{$uuid};
                if ($node != null) {
                    if ($enabled == "0" || $enabled == "1") {
                        $node->enabled = (string)$enabled;
                    } elseif ((string)$node->enabled == "1") {
                        $node->enabled = "0";
                    } else {
                        $node->enabled = "1";
                    }
                    $result['result'] = $node->enabled;
                    // if item has toggled, serialize to config and save
                    $mdlCP->serializeToConfig();
                    Config::getInstance()->save();
                    $this->reloadConfig($mdlCP);
                }
            }
        }
        return $result;
    }

    /**
     * search captive portal Ip rules
     * @param int $zoneid zone number
     * @return array
     */
    public function searchIpRulesAction($zoneid = 0)
    {
        $mdlCP = new CaptivePortal();
        $cpZone = $mdlCP->getByZoneID($zoneid);
        if ($cpZone != null) {
            $grid = new UIModelGrid($cpZone->ipAccess->ipRule);
            return $grid->fetchBindRequest(
                $this->request,
                array("enabled", "ip", "description", "shaperUpload", "shaperDownload"),
                "description"
            );
        } else {
            // illegal zone, return empty response
            return array();
        }
    }
}
