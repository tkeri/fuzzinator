var ws;
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
                console.log(data)
                break;
            case "new_issue":
                console.log(data)
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

function iterateAttributesAndFormHTMLLabels(json_o){
    var s = "";
    Object.keys(json_o).forEach(function(k){
        if (typeof json_o[k] == 'object'){
            s+='<label><font color=green>' + k + '</font></label><br />';
            s+=iterateAttributesAndFormHTMLLabels(json_o[k]);
        } else {
            s+='<label><font color=blue>'+json_o[k]+'</font></label><br />';
        }
    });
    return s;
};

function createContentFromJson(json_o, tag_id) {
    var elem = document.createElement('textarea');
    elem.innerHTML = json_o;
    var decoded = elem.value;
    decoded = decoded.replace( /'/g, '"')
// TODO: test print
    console.log(decoded);
    decoded = JSON.parse(decoded);
    var html = iterateAttributesAndFormHTMLLabels(decoded);
    $("#" + tag_id).html(html);
}

startWebsocket();
var content_update =  setInterval(updateContent, 4000);
