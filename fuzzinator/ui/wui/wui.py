#! /usr/bin/python3

#TODO: add license

# Utility libraries
import datetime
import json
import logging
import os
import signal
import time

# TODO: HACK
from bson.objectid import ObjectId
from functools import partial
from multiprocessing import Lock, Process, Queue

# Webserver stuff
from tornado import websocket, web, ioloop

# Fuzzinator stuff
from fuzzinator import Controller
from fuzzinator.config import config_get_with_writeback
from fuzzinator.ui import build_parser, process_args
from .wui_listener import WuiListener
from fuzzinator.listener import EventListener

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3

logger = logging.getLogger(__name__)


class ObjectIdEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, bytes):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

class SocketHandler(websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        self.wui = kwargs.pop('wui')
        self.controller = kwargs.pop('controller')
        super(SocketHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self):
        self.wui.registerWs(self)

    def on_message(self, message):
        request = json.loads(message)
        action = request['action']
        if action == 'get_stats':
            self.send_message('get_stats', self.controller.db.stat_snapshot(None))

        elif action == 'get_issues':
            self.send_message('get_issues', self.controller.db.all_issues())

        elif action == 'get_jobs':
           for (ident, fuzzer, sut, cost, batch) in self.controller.iter_running_jobs():
               self.send_message('new_fuzz_job', dict(ident=ident, fuzzer=fuzzer, sut=sut, cost=cost, batch=batch))

        elif action == 'get_issue':
            issue_dict = self.controller.db.find_issue_by_id(request['_id'])

            self.send_message('get_issue', issue_dict)

        elif action == 'delete_issue':
            self.controller.db.remove_issue_by_id(request['_id'])

        else:
            logger.warning('ERROR: Invalid {action} message!'.format(action=action))

    def on_close(self):
        self.wui.unregisterWs(self)

    def send_message(self, action, data):
        message = {
            "action": action,
            "data": data
        }
        try:
            self.write_message(json.dumps(message, cls=ObjectIdEncoder))
        except Exception as e:
            logger.error(e)
            self.on_close()


class IssueHandler(web.RequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = kwargs.pop('db')
        super(IssueHandler, self).__init__(*args, **kwargs)

    def get(self, issue_id):
        issue = self.db.find_issue_by_id(issue_id)
        issue_json = json.dumps(issue, cls=ObjectIdEncoder)
        self.render('issue.html', issue=issue, issue_json=issue_json)

# route to index.html
class IndexHandler(web.RequestHandler):

    def __init__(self, *args, **kwargs):
        self.db = kwargs.pop('db')
        super(IndexHandler, self).__init__(*args, **kwargs)

    def get(self):
        self.render('index.html')


class Wui(EventListener):

    def __init__(self, controller, settings, port):
        self.events = Queue()
        self.lock = Lock()
        self.controller = controller
        self.app = web.Application([
                    (r'/', IndexHandler, dict(db=controller.db)),
                    (r'/issue/([0-9a-f]{24})', IssueHandler, dict(db=controller.db)),
                    (r'/websocket', SocketHandler, dict(controller=controller, wui=self))
                ], autoreload=False, **settings)
        self.server = self.app.listen(port)
        self.socket_list = []

    def registerSignals(self):
        signal.signal(signal.SIGTERM, partial(self.sig_handler, self))
        signal.signal(signal.SIGINT, partial(self.sig_handler, self))

    def registerWs(self, wsSocket):
        self.socket_list.append(wsSocket)

    def unregisterWs(self, wsSocket):
        self.socket_list.remove(wsSocket)

    def stopWs(self):
        for wsSocket in self.socket_list:
            wsSocket.close()

    def send_message(self, action, data):
        for wsSocket in self.socket_list:
            wsSocket.send_message(action, data)

    def new_fuzz_job(self, **kwargs):
        self.send_message('new_fuzz_job', kwargs)

    def new_reduce_job(self, **kwargs):
        self.send_message('new_reduce_job', kwargs)

    def new_update_job(self, **kwargs):
        self.send_message('new_update_job', kwargs)

    def job_progress(self, **kwargs):
        self.send_message('job_progress', kwargs)

    def remove_job(self, **kwargs):
        self.send_message('remove_job', kwargs)

    def activate_job(self, **kwargs):
        self.send_message('activate_job', kwargs)

    def new_issue(self, **kwargs):
        self.send_message('new_issue', kwargs)

    def update_fuzz_stat(self):
        self.send_message('update_fuzz_stat', self.controller.db.stat_snapshot(None))

    def warning(self, msg):
        logger.warning(msg)

    def process_loop(self):
        while True:
            try:
                event = self.events.get_nowait()
                if hasattr(self, event['fn']):
                    getattr(self, event['fn'])(**event['kwargs'])
            except:
                break

    @staticmethod
    def sig_handler(wui, sig, frame):
        io_loop = ioloop.IOLoop.instance()

        def stop_loop(deadline):
            now = time.time()
            if now < deadline:
                logging.info('Waiting for next tick')
                io_loop.add_timeout(now + 1, stop_loop, deadline)
            else:
                io_loop.stop()
                logging.info('Shutdown finally')

        def shutdown():
            logging.info('Stopping http server')
            wui.stopWs()
            wui.server.stop()
            logging.info('Will shutdown in %s seconds ...',
                        MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
            stop_loop(time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)

        logger.warning('Caught signal: %s', sig)
        io_loop.add_callback_from_signal(shutdown)



def execute(args=None, parser=None):
    parser = build_parser(parent=parser)
    arguments = parser.parse_args(args)
    error_msg = process_args(arguments)
    if error_msg:
        parser.error(error_msg)

    port = int(config_get_with_writeback(arguments.config, 'fuzzinator.wui', 'port', '8080'))
    print('You can open wui on http://localhost:{port}'.format(port=port))
    settings = dict(
        template_path = os.path.join(os.path.dirname(__file__), 'templates'),
        static_path = os.path.join(os.path.dirname(__file__), 'static'),
        debug = True
    )

    controller = Controller(config=arguments.config)
    wui = Wui(controller, settings, port)
    controller.listener += WuiListener(wui.events, wui.lock)
    fuzz_process = Process(target=controller.run, args=())

    iol = ioloop.IOLoop.instance()
    iolcb = ioloop.PeriodicCallback(wui.process_loop, 1000)

    wui.registerSignals()

    try:
        fuzz_process.start()
        iolcb.start()
        iol.start()
    except KeyboardInterrupt:
        pass
    except Exception:
        os.kill(fuzz_process.pid, signal.SIGINT)
    else:
        os.kill(fuzz_process.pid, signal.SIGINT)
    finally:
        iol.add_callback(iol.stop)

