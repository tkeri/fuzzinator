newEcho();

function newEcho() {
    var ws = new WebSocket("ws://localhost:8080/websocket");
    var out;
    ws.onopen = function () {
        ws.send("Kuflik!");
    };
    ws.onmessage = function (evt) {
        console.log(evt.data);
    };
}