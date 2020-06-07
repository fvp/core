{#

OPNsense® is Copyright © 2014 – 2015 by Deciso B.V.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1.  Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2.  Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

#}
<script src="/ui/js/moment-with-locales.min.js" type="text/javascript"></script>

<script type="text/javascript">

    $( document ).ready(function() {

        function updateZones() {
            ajaxGet("/api/captiveportal/settings/searchZones/", {}, function(data, status) {
                if (status == "success") {
                    $('#cp-zones').html("");
                    $.each(data.rows, function(key, value) {
                        $('#cp-zones').append($("<option></option>").attr("value", value.zoneid).text(value.description));
                    });
                    $('.selectpicker').selectpicker('refresh');
                    // link on change event
                    $('#cp-zones').on('change', function(){
                        loadTabs();
                    });
                    // initial load tabs
                    loadTabs();
                }
            });
        }

        
        function loadTabs() {
            var zoneid = $('#cp-zones').find("option:selected").val();
            $('#grid-mac').bootgrid('destroy');
            $('#grid-ip').bootgrid('destroy');

            $("#grid-mac").UIBootgrid(
                {   search:'/api/captiveportal/hostaccess/searchMacRules/'+zoneid+'/',
                    get:'/api/captiveportal/hostaccess/getMacRule/'+zoneid+'/',
                    set:'/api/captiveportal/hostaccess/setMacRule/'+zoneid+'/',
                    add:'/api/captiveportal/hostaccess/addMacRule/'+zoneid+'/',
                    del:'/api/captiveportal/hostaccess/delMacRule/'+zoneid+'/',
                    toggle:'/api/captiveportal/hostaccess/toggleMacRule/'+zoneid+'/'
                }
            );
            
            $("#grid-ip").UIBootgrid(
                {   search:'/api/captiveportal/hostaccess/searchIpRules/'+zoneid+'/',
                    get:'/api/captiveportal/hostaccess/getIpRule/'+zoneid+'/',
                    set:'/api/captiveportal/hostaccess/setIpRule/'+zoneid+'/',
                    add:'/api/captiveportal/hostaccess/addIpRule/'+zoneid+'/',
                    del:'/api/captiveportal/hostaccess/delIpRule/'+zoneid+'/',
                    toggle:'/api/captiveportal/hostaccess/toggleIpRule/'+zoneid+'/'
                }
            );             
        }

        // init with first selected zone
        updateZones();
    });


</script>

<div class="table-responsive">
    <div class="col-sm-12">
        <div class="pull-right">
            <select id="cp-zones" class="selectpicker" data-width="200px"></select>
        </div>
    </div>
    <div  class="col-sm-12">
        <ul class="nav nav-tabs" data-tabs="tabs" id="maintabs">
            <li class="active"><a data-toggle="tab" href="#mac">MAC</a></li>
            <li><a data-toggle="tab" href="#ip">IP</a></li>
        </ul>

        <div class="tab-content content-box">
            <div id="mac" class="tab-pane fade in active">
                <table id="grid-mac" class="table table-condensed table-hover table-striped table-responsive" data-editDialog="DialogHostAccessMac">
                    <thead>
                    <tr>
                        <th data-column-id="enabled" data-width="6em" data-type="string" data-formatter="rowtoggle">{{ lang._('Enabled') }}</th>
                        <th data-column-id="action" data-type="string">{{ lang._('Action') }}</th>
                        <th data-column-id="mac" data-type="string">{{ lang._('Mac') }}</th>
                        <th data-column-id="description" data-type="string">{{ lang._('Description') }}</th>
                        <th data-column-id="shaperDownload" data-type="string">{{ lang._('Shaper Download') }}</th>
                        <th data-column-id="shaperUpload" data-type="string">{{ lang._('Shaper Upload') }}</th>
                        
                        <th data-column-id="commands" data-width="7em" data-formatter="commands" data-sortable="false">{{ lang._('Commands') }}</th>
                        <th data-column-id="uuid" data-type="string" data-identifier="true" data-visible="false">{{ lang._('ID') }}</th>
                    </tr>
                    </thead>
                    <tbody>
                    </tbody>
                    <tfoot>
                    <tr>
                        <td></td>
                        <td>
                            <button data-action="add" type="button" class="btn btn-xs btn-default"><span class="fa fa-plus"></span></button>
                            <button data-action="deleteSelected" type="button" class="btn btn-xs btn-default"><span class="fa fa-trash-o"></span></button>
                        </td>
                    </tr>
                    </tfoot>
                </table>
            </div>
            <div id="ip" class="tab-pane fade in">
                <table id="grid-ip" class="table table-condensed table-hover table-striped table-responsive" data-editDialog="DialogHostAccessIp">
                    <thead>
                    <tr>
                        <th data-column-id="enabled" data-width="6em" data-type="string" data-formatter="rowtoggle">{{ lang._('Enabled') }}</th>
                        <th data-column-id="ip" data-type="string">{{ lang._('IP Address') }}</th>
                        <th data-column-id="description" data-type="string">{{ lang._('Description') }}</th>
                        <th data-column-id="shaperDownload" data-type="string">{{ lang._('Shaper Download') }}</th>
                        <th data-column-id="shaperUpload" data-type="string">{{ lang._('Shaper Upload') }}</th>              
                        
                        <th data-column-id="commands" data-width="7em" data-formatter="commands" data-sortable="false">{{ lang._('Commands') }}</th>
                        <th data-column-id="uuid" data-type="string" data-identifier="true" data-visible="false">{{ lang._('ID') }}</th>
                    </tr>
                    </thead>
                    <tbody>
                    </tbody>
                    <tfoot>
                    <tr>
                        <td></td>
                        <td>
                            <button data-action="add" type="button" class="btn btn-xs btn-default"><span class="fa fa-plus"></span></button>
                            <button data-action="deleteSelected" type="button" class="btn btn-xs btn-default"><span class="fa fa-trash-o"></span></button>
                        </td>
                    </tr>
                    </tfoot>
                </table>
            </div>
        </div>
    </div>        
</div>        

{# include dialogs #}
{{ partial("layout_partials/base_dialog",['fields':formDialogHostAccessMac,'id':'DialogHostAccessMac','label':'Edit MAC Access Rule'])}}
{{ partial("layout_partials/base_dialog",['fields':formDialogHostAccessIp,'id':'DialogHostAccessIp','label':'Edit IP Access Rule'])}}