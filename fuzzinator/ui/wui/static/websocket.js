var ws;
var jobsDict = {};
function startWebsocket() {
    ws = new WebSocket("ws://10.6.11.69:8080/websocket");
    ws.onopen = function () {
        updateContent();
    };
    ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        var action = msg.action;
        var data = msg.data;
        switch (action) {
            case "set_stats":
                var stats_content = "";
                Object.keys(data).forEach(function(k){
                    stats_content += '<div class="list-group-item">\
                            <div class="row">\
                            <div class="col-sm issue_id">' + k + '</div>\
                            <div class="col-sm issue_reported">' + data[k].exec + '</div>\
                            <div class="col-sm issue_seen">' + data[k].issues + '</div>\
                            <div class="col-sm issue_count">' + data[k].unique + '</div>\
                            </div>\
                            </div>';
                });
                $("#stats_body").html(stats_content);
                break;
            case "set_issues":
                var issues_content = "";
                Object.keys(data).forEach(function(k){
                    issues_content += '\
                            <a href="/issue/' + data[k]._id + '" class="list-group-item list-group-item-action">\
                            <div class="row">\
                            <div class="col-sm issue_id" data-togle="tool-tip" title="' + data[k].id + '">' + data[k].id + '</div>\
                            <div class="col-sm issue_fuzzer" data-togle="tool-tip" title="' + data[k].fuzzer + '">' + data[k].fuzzer + '</div>\
                            <div class="col-sm issue_seen">' + data[k].first_seen + '</div>\
                            <div class="col-sm issue_count">' + data[k].count + '</div>\
                            <div class="col-sm issue_reported">' + data[k].reduced + '</div>\
                            <div class="col-sm issue_reported">' + data[k].reported + '</div>\
                            </div>\
                            </a>';
                });
               $("#issues_body").html(issues_content);
                break;
            case "new_fuzz_job":
                var job_content = "";
                var jsonData = JSON.parse(data);
                jobsDict[jsonData.ident] = jsonData.batch;
                console.log('new fuzz: ' + JSON.parse(data));
                job_content += '\
                <table class="table">\
                    <thead> \
                       <tr> \
                          <th align="center">Fuzz Job</th>\
                        </tr>\
                    </thead>\
                    <tbody>\
                    <tr>\
                        <th>Fuzzer</th>\
                        <td>' + jsonData.fuzzer + '</td>\
                    </tr>\
                    <tr>\
                        <th>Sut</th>\
                        <td>' + jsonData.sut + '</td>\
                    </tr>\
                    <tr>\
                        <th>Cost</th>\
                        <td>' + jsonData.cost + '</td>\
                    </tr>\
                    <tr>\
                        <th>Progress</th>\
                        <td id="' + jsonData.ident + '"> 0 </td>\
                    </tr>\
                    </tbody>\
                </table>';
                $("#job_body").html(job_content);
                console.log(document.getElementById(jsonData.ident));
                break;
            case "job_progress":
                var jsonData = JSON.parse(data);
                console.log('ident to udpate' + jsonData.ident);
                console.log(document.getElementsByClassName(jsonData.ident));

                $(document).ready(function(){
                    //console.log(jsonData.ident + ':' + jsonData.progress + document.getElementById(jsonData.ident));
                });
                $("#" + jsonData.ident).ready(function() {
                    $("#" + jsonData.ident).text(jsonData.progress);
                });
                break;
        }
    };
};
function updateContent() {
        var request = {
            action: 'action'
        };
        request.action = 'get_issues';
        ws.send(JSON.stringify(request));
// TEST print
        console.log(request.action);

        request.action = 'get_stats';
        ws.send(JSON.stringify(request));
// TEST print
        console.log(request.action);
};


function iterateAttributesAndFormHTMLLabels(json_o, count=0){
    var s = '';

    if (json_o instanceof Array) {
        json_o.forEach(function(element, index, array) {
            s += iterateAttributesAndFormHTMLLabels(element, count);
        });
    } else if (typeof json_o == 'object') {
        Object.keys(json_o).forEach(function(k){
            if (json_o[k] !== null) {
                s += '<b><label style="text-indent:' + count * 15 + 'px">' + k + ': </label></b><br/>';
                s += iterateAttributesAndFormHTMLLabels(json_o[k], count + 2)
            }
        });
    } else {
        s += '<label style="text-indent:' + count * 15 + 'px"><pre>' + json_o + '</pre></label><br />';
    }
    return s;
};

function createContentFromJson(json_o, tag_id) {
    var html = iterateAttributesAndFormHTMLLabels(json_o);
    $("#" + tag_id).html(html);
}

startWebsocket();
var content_update =  setInterval(updateContent, 4000);
