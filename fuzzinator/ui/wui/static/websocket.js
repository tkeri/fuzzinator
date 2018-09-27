var ws;
function startWebsocket() {
    ws = new WebSocket("ws://" + window.location.host + "/websocket");
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
                reduced_icon = "";
                reported_icon = "";
                var issues_content = "";
                Object.keys(data).forEach(function(k){
                    reported_icon = setRightIcon(data[k].reported);
                    reduced_icon = setRightIcon(data[k].reduced);
                    issues_content += '\
                            <a href="/issue/' + data[k]._id + '" class="list-group-item list-group-item-action">\
                            <div class="row">\
                            <div class="col-sm issue_id" data-togle="tool-tip" title="' + data[k].id + '">' + data[k].id + '</div>\
                            <div class="col-sm issue_fuzzer" data-togle="tool-tip" title="' + data[k].fuzzer + '">' + data[k].fuzzer + '</div>\
                            <div class="col-sm issue_seen">' + data[k].first_seen + '</div>\
                            <div class="col-sm issue_count">' + data[k].count + '</div>\
                            <div class="col-sm issue_reported">' + reduced_icon  + '</div>\
                            <div class="col-sm issue_reported">' + reported_icon  + '</div>\
                            </div>\
                            </a>';
                });
                $("#issues_body").html(issues_content);
                break;
            case "new_fuzz_job":
                var job_content = "";
                job_content += '\
                <table id="' + data.ident + '" class="table table-bordered inactive_job">\
                    <thead> \
                       <tr> \
                          <th colspan="2" align="center">Fuzz Job</th>\
                        </tr>\
                    </thead>\
                    <tbody>\
                    <tr>\
                        <th>Fuzzer</th>\
                        <td>' + data.fuzzer + '</td>\
                    </tr>\
                    <tr>\
                        <th>Sut</th>\
                        <td>' + data.sut + '</td>\
                    </tr>\
                    <tr>\
                        <th>Cost</th>\
                        <td>' + data.cost + '</td>\
                    </tr>\
                    <tr>\
                        <th>Progress</th>\
                        <td>\
                            <progress class="pBar" id="' + data.ident + '_progBar" value="0" max="' + data.batch + '" />\
                        </td>\
                    </tr>\
                    </tbody>\
                </table>';
                $("#job_container").prepend(job_content);
                break;
            case "job_progress":
                $("#" + data.ident + "_progBar").attr('value', data.progress);
                console.log('progress: ' + data.progress)
                break;
            case "remove_job":
                $("#" + data.ident).remove();
                break;
            case "activate_job":
                $("#" + data.ident).removeClass("inactive_job");
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

function setRightIcon(data) {
    if (data === null || data === false) {
        return '<i class="far fa-times-circle"></i>';
    }

    return '<i class="far fa-check-circle"></i>';
};

startWebsocket();
var content_update =  setInterval(updateContent, 4000);
