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
            case "get_stats":
                Object.keys(data).forEach(function(k){
                    var content = document.querySelector("#stat-card-template").content.cloneNode(true);
                    content.querySelector(".fuzzer").textContent = k;
                    content.querySelector(".executed").textContent = data[k].exec;
                    content.querySelector(".failed").textContent = data[k].issues;
                    content.querySelector(".unique").textContent = data[k].unique;
                    $("#stats").append(document.importNode(content, true));
                });
                break;

            case "get_issues":
                Object.keys(data).forEach(function(k){
                    var content = document.querySelector("#issue-card-template").content.cloneNode(true);
                    content.querySelector(".issue-id").textContent = data[k].id;
                    content.querySelector(".issue-id").setAttribute("onclick", "open_issue('" + data[k]._id + "')");
                    content.querySelector(".issue-id").setAttribute("title", data[k].id);
                    content.querySelector(".sut-id").textContent = data[k].sut;
                    content.querySelector(".fuzzer-id").textContent = data[k].fuzzer;
                    content.querySelector(".date_range").textContent = data[k].first_seen + " .. " + data[k].last_seen;
                    content.querySelector(".count").textContent = data[k].count;
                    if (data[k].reduced)
                        content.querySelector(".reduced").textContent = 'crop';
                    if (data[k].reported)
                        content.querySelector(".reported").textContent = 'link';
                    $("#issues").append(document.importNode(content, true));
                 });
                break;

            case "get_issue":
                var content = document.querySelector("#issue-details-template").content.cloneNode(true);
                content.querySelector(".issue-id").textContent = data.id;
                content.querySelector(".sut-id").textContent = data.sut;
                content.querySelector(".fuzzer-id").textContent = data.fuzzer;

                if ('first_seen' in data && 'last_seen' in data)
                    content.querySelector(".date_range").textContent = data.first_seen + " .. " + data.last_seen;

                if ('count' in data)
                    content.querySelector(".count").textContent = data.count;

                if (data.reduced)
                    content.querySelector(".reduced").textContent = 'crop';

                if (data.reported)
                    content.querySelector(".reported").textContent = 'link';

                $("#issue").empty();
                $("#issue").append(document.importNode(content, true));
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
                $("#jobs").append(new_node);
                break;

            case "new_reduce_job":
                var content = document.querySelector("#reduce-job-template").content.cloneNode(true);
                content.querySelector('.card').id = 'job-' + data.ident;
                content.querySelector(".reduce-job-id").textContent = data.ident;
                content.querySelector(".reduce-job-sut").textContent = data.sut;
                content.querySelector(".reduce-job-issue").textContent = data.issue_id;
                content.querySelector(".progress-bar").setAttribute("data-maxvalue", data.size);
                $("#jobs").append(document.importNode(content, true));
                break;

            case "new_update_job":
                var content = document.querySelector("#update-job-template").content.cloneNode(true);
                content.querySelector('.card').id = 'job-' + data.ident;
                content.querySelector(".update-job-id").textContent = data.ident;
                content.querySelector(".update-job-sut").textContent = data.sut;
                $("#jobs").append(document.importNode(content, true));
                break;

            case "job_progress":
                var job = document.querySelector('#job-' + data.ident);

                if (job === null)
                    break;

                var progress = job.querySelector('.progress-bar');
                var percent = Math.round(data.progress / progress.getAttribute('data-maxvalue') * 100);
                progress.style = "width: " + percent + "%";
                progress.setAttribute('aria-valuenow', percent);
                progress.textContent = percent + "%";
                break;

            case "activate_job":
                var job_card = document.querySelector('#job-' + data.ident);
                if (job_card !== null)
                    job_card.classList.replace("bg-secondary", "bg-info");
                break;

            case "remove_job":
                $("#job-" + data.ident).remove();
                break;

            case "new_issue":
                var content = document.querySelector("#issue-card-template").content.cloneNode(true);
                content.querySelector(".issue-id").textContent = data.id;
                content.querySelector(".sut-id").textContent = data.sut;
                content.querySelector(".fuzzer-id").textContent = data.fuzzer;
                content.querySelector(".first-seen").textContent = data.first_seen;
                content.querySelector(".count").textContent = 1;
                if (data.reduced)
                    content.querySelector(".reduced").textContent = 'crop';
                if (data.reported)
                    content.querySelector(".reported").textContent = 'link';
                var issue_list = document.querySelector("#issues");
                issue_list.insertBefore(document.importNode(content, true), issue_list.childNodes[0] || null);
                break;

        }
    };
};

function updateContent() {
    ws.send(JSON.stringify({"action": 'get_issues'}));
    ws.send(JSON.stringify({"action": 'get_jobs'}));
    ws.send(JSON.stringify({"action": 'get_stats'}));
};

startWebsocket();
//var content_update =  setInterval(updateContent, 4000);

function expandAll() {
    $('.panel-collapse').collapse('show');
};

function collapseAll() {
    $('.panel-collapse').collapse('hide');
};
