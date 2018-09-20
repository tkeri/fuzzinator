newEcho();

function newEcho() {
    var ws = new WebSocket("ws://10.6.11.69:8080/websocket");
    ws.onopen = function () {
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
    ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        var action = msg.action;
        var data = msg.data;
        switch (action) {
            case "set_stats":
                var stats_content = "";
                $.each(data, function(i, item) {
                    stats_content += '<li id="'+ i +'" class="list-group-item">' + i + '<span class="badge">' + data[i].exec + '</span></li>';
                });
                $("#stats_body").html(stats_content);
                break;
            case "set_issues":
                var issues_content = "";
                $.each(data, function(i, item) {
                    issues_content += '\
                            <a href="/issue/' + item._id + '" class="list-group-item list-group-item-action">\
                            <div class="row">\
                            <div class="col-sm issue_id">' + item.id + '</div>\
                            <div class="col-sm issue_reported">' + item.reported + '</div>\
                            <div class="col-sm issue_seen">' + item.first_seen + '</div>\
                            <div class="col-sm issue_count">' + item.count + '</div>\
                            </div>\
                            </a>';
                });
                $("#issues_body").html(issues_content);
                break;
        }
    };
};
