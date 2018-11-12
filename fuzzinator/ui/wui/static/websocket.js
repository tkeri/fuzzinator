var ws;
function startWebsocket() {
    ws = new WebSocket("ws://" + window.location.host + "/websocket");
    ws.onopen = function () {
        updateContent();
        var status_dot = document.querySelector('.websocket-status');
        status_dot.title = 'online';
        status_dot.classList.add('bg-ok');
    };
    ws.onclose = function() {
        var status_dot = document.querySelector('.websocket-status');
        status_dot.title = 'offline';
        status_dot.classList.remove('bg-ok');
    };

    ws.onmessage = function (evt) {
        var msg = JSON.parse(evt.data);
        // TODO: debug print
        console.log(msg);
        var action = msg.action;
        var data = msg.data;
        switch (action) {
            case "get_stats":
                var prev_stats = document.querySelectorAll('.stats-entry');
                if (prev_stats) {
                    prev_stats.forEach(function(stat_entry) { stat_entry.remove(); });
                }
                Object.keys(data).forEach(function(k){
                    var content = document.querySelector("#stat-card-template").content.cloneNode(true);
                    content.firstElementChild.classList.add(k);
                    content.firstElementChild.classList.add('stats-entry');
                    content.querySelector(".fuzzer").textContent = k;
                    content.querySelector(".executed").textContent = data[k].exec;
                    content.querySelector(".failed").textContent = data[k].issues;
                    content.querySelector(".unique").textContent = data[k].unique;
                    $("#stats").append(document.importNode(content, true));
                });
                break;

            case "update_fuzz_stat":
                if (active_page != 'stats') {
                   break;
                }
                Object.keys(data).forEach(function(k){
                    var content = document.querySelector("." + k);
                    content.querySelector(".executed").textContent = data[k].exec;
                    content.querySelector(".failed").textContent = data[k].issues;
                    content.querySelector(".unique").textContent = data[k].unique;
                });
                break;

            case "get_issues":
                var i = 0;
                var issues_size = data.issues_size;
                var counter = issues_size / 10;
                var issues = data.issues;
                var page_id = data.page_id;
                var prev_issues = document.querySelectorAll('.issues-entry');
                var prev_paginations = document.querySelectorAll('.paginations-entry');

                if (prev_issues) {
                    prev_issues.forEach(function(issue_entry) { issue_entry.remove(); });
                }
                if (prev_paginations) {
                    prev_paginations.forEach(function(pagination_entry) { pagination_entry.remove(); });
                }

                Object.keys(issues).forEach(function(k){
                    var content = document.querySelector("#issue-card-template").content.cloneNode(true);
                    content.firstElementChild.classList.add('issues-entry');
                    content.querySelector(".card").id = issues[k]._id;
                    content.querySelector(".reduce-issue").setAttribute("onclick", "reduce_issue('" + issues[k]._id + "')");
                    content.querySelector(".validate-issue").setAttribute("onclick", "validate_issue('" + issues[k]._id + "')");
                    content.querySelector(".issue-ref").textContent = issues[k].id;
                    content.querySelector(".issue-ref").setAttribute("href", "/issue/" + issues[k]._id);
                    content.querySelector(".delete-issue").setAttribute("onclick", "delete_issue('" + issues[k]._id + "')");
                    content.querySelector(".issue-id").setAttribute("title", issues[k].id);
                    content.querySelector(".sut-id").textContent = issues[k].sut;
                    content.querySelector(".fuzzer-id").textContent = issues[k].fuzzer;
                    content.querySelector(".date_range").textContent = issues[k].first_seen + " .. " + issues[k].last_seen;
                    content.querySelector(".count").textContent = issues[k].count;
                    if (issues[k].reduced)
                        content.querySelector(".reduced").textContent = 'crop';
                    if (issues[k].reported)
                        content.querySelector(".reported").textContent = 'link';
                    $("#issues").append(document.importNode(content, true));
                 });

                do {
                    i++;
                    var content = document.querySelector("#pagination-card-template").content.cloneNode(true);
                    if (i == page_id) {
                        content.firstElementChild.classList.add('active');
                    }
                    content.firstElementChild.classList.add('paginations-entry');
                    content.querySelector(".page-link").text = i;
                    content.querySelector(".page-item").setAttribute("onmousedown", "paginationIssues(" + i + ")");
                    content.querySelector(".page-item").setAttribute("id", "page_" + i);
                    $("#pagination-buttons").append(document.importNode(content, true));
                } while (i < counter);
                break;

            case "new_fuzz_job":
                if (document.getElementById("job-" + data.ident))
                    break;

                var content = document.querySelector("#fuzz-job-template").content.cloneNode(true);
                content.querySelector(".fuzz-job-id").textContent = data.ident;
                content.querySelector(".fuzz-job-fuzzer").textContent = data.fuzzer;
                content.querySelector(".fuzz-job-sut").textContent = data.sut;
                content.querySelector(".progress-bar").setAttribute("data-maxvalue", data.batch);
                var new_node = document.importNode(content, true);
                new_node.querySelector('.card').id = 'job-' + data.ident;
                if (data.status == 'active') {
                    new_node.querySelector('.card').classList.add('bg-info');
                }
                $("#jobs").append(new_node);
                break;

            case "new_reduce_job":
                var content = document.querySelector("#reduce-job-template").content.cloneNode(true);
                content.querySelector('.card').id = 'job-' + data.ident;
                content.querySelector(".reduce-job-id").textContent = data.ident;
                content.querySelector(".reduce-job-sut").textContent = data.sut;
                content.querySelector(".reduce-job-issue").textContent = data.issue_id;
                content.querySelector(".progress-bar").setAttribute("data-maxvalue", data.size);
                var new_node = document.importNode(content, true);
                if (data.status == 'active') {
                    new_node.querySelector('.card').classList.add('bg-info');
                }
                $("#jobs").append(new_node);
                break;

            case "new_update_job":
                var content = document.querySelector("#update-job-template").content.cloneNode(true);
                content.querySelector('.card').id = 'job-' + data.ident;
                content.querySelector(".update-job-id").textContent = data.ident;
                content.querySelector(".update-job-sut").textContent = data.sut;
                var new_node = document.importNode(content, true);
                if (data.status == 'active') {
                    new_node.querySelector('.card').classList.add('bg-info');
                }
                $("#jobs").append(new_node);
                break;

            case "new_validate_job":
                var content = document.querySelector("#validate-job-template").content.cloneNode(true);
                content.querySelector('.card').id = 'job-' + data.ident;
                content.querySelector(".validate-job-id").textContent = data.ident;
                content.querySelector(".validate-job-sut").textContent = data.sut;
                content.querySelector(".validate-job-issue").textContent = data.issue_id;
                var new_node = document.importNode(content, true);
                if (data.status == 'active') {
                    new_node.querySelector('.card').classList.add('bg-info');
                }
                $("#jobs").append(new_node);
                break;

            case "job_progress":
                var job = document.querySelector('#job-' + data.ident);

                if (job === null)
                    break;

                var progress = job.querySelector('.progress-bar');
                var percent = Math.round(data.progress / progress.getAttribute('data-maxvalue') * 100);
                progress.style = "width: " + percent + "%";
                progress.setAttribute('aria-valuenow', percent);
                job.classList.toggle('progress_tick');

                var progress_text = job.querySelector('.progress-text');
                progress_text.textContent = percent + '%';

                break;

            case "activate_job":
                var job_card = document.querySelector('#job-' + data.ident);
                if (job_card !== null && job_card.classList.contains('bg-secondary'))
                    job_card.classList.replace("bg-secondary", "bg-info");
                break;

            case "remove_job":
                $("#job-" + data.ident).remove();
                break;

            case "new_issue":
                data = data.issue;
                var content = document.querySelector("#issue-card-template").content.cloneNode(true);
                content.querySelector(".card").id = data._id;
                content.querySelector(".issue-id").textContent = data.id;
                content.querySelector(".issue-id").setAttribute("onclick", "open_issue('" + data._id + "')");
                content.querySelector(".reduce-issue").setAttribute("onclick", "reduce_issue('" + data._id + "')");
                content.querySelector(".validate-issue").setAttribute("onclick", "validate_issue('" + data._id + "')");
                content.querySelector(".delete-issue").setAttribute("onclick", "delete_issue('" + data._id + "')");
                content.querySelector(".sut-id").textContent = data.sut;
                content.querySelector(".fuzzer-id").textContent = data.fuzzer;
                content.querySelector(".date_range").textContent = data.first_seen + " .. " + data.last_seen;
                content.querySelector(".count").textContent = 1;
                if (data.reduced)
                    content.querySelector(".reduced").textContent = 'crop';
                if (data.reported)
                    content.querySelector(".reported").textContent = 'link';
                $("#issues").prepend(document.importNode(content, true));
                fire_work();
                break;
        }
    };
};

function updateContent() {
    ws.send(JSON.stringify({"action": 'get_jobs'}));
    switch(active_page) {
        case "issues": ws.send(JSON.stringify({"action": 'get_issues'})); break;
        case "stats": ws.send(JSON.stringify({"action": 'get_stats'})); break;
        default: break;
    }
};

function paginationIssues(page) {
    document.querySelector(".paginations-entry.active").classList.remove("active");
    document.querySelector("#page_" + page).classList.add("active");
    ws.send(JSON.stringify({"action": 'get_issues', "data": page}));
    console.log(page);
};

function websocket_toggle_connection() {
    console.log("state: ");
    console.log(ws.readyState);
    if (ws.readyState == WebSocket.OPEN) {
        ws.close();
    } else {
        startWebsocket();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    startWebsocket();
    var status_dot = document.querySelector('.websocket-status');
    status_dot.addEventListener('click', websocket_toggle_connection);
});

