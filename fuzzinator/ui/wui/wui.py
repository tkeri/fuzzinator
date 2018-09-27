#! /usr/bin/python3

#TODO: add license

# Utility libraries
import datetime
import os
import json
import signal


from multiprocessing import Lock, Process, Queue
# TODO: HACK
from bson.objectid import ObjectId

# Webserver stuff
from tornado import websocket, web, ioloop
from tornado.options import define, options

# Fuzzinator stuff
from fuzzinator import Controller
from fuzzinator.config import config_get_with_writeback
from fuzzinator.ui import build_parser, process_args
from .wui_listener import WuiListener
from fuzzinator.listener import EventListener


class ObjectIdEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
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
        print("WebSocket opened")

    def on_message(self, message):
        request = json.loads(message)
        action = request['action']
        if action == 'get_stats':
            stats = self.controller.db.stat_snapshot(None)
            issues = self.controller.db.all_issues()

            self.send_message('set_stats', stats)
#TEST PRINT:
            #print('WS SEND: set_stats')
        elif action == 'get_issues':
            issues = self.controller.db.all_issues()

            self.send_message('set_issues', issues)
#TEST PRINT:
            #print('WS SEND: set_issues')
        else:
            print('ERROR: Invalid {action} message!'.format(action=action))

    def on_close(self):
        self.wui.unregisterWs(self)
        print("WebSocket closed")

    def send_message(self, action, data):
        message = {
            "action": action,
            "data": data
        }
        try:
            self.write_message(json.dumps(message, cls=ObjectIdEncoder))
        except Exception as e:
            print(str(e))
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
        issues = self.db.all_issues()
        self.render('index.html')


class Wui(EventListener):

    def __init__(self, controller, settings, port):
        self.events = Queue()
        self.lock = Lock()
        controller.listener += self
        self.app = web.Application([
                    (r'/', IndexHandler, dict(db=controller.db)),
                    (r'/issue/([0-9a-f]{24})', IssueHandler, dict(db=controller.db)),
                    (r'/websocket', SocketHandler, dict(controller=controller, wui=self))
                ], **settings)
        self.app.listen(port)
        self.socket_list = []

    def registerWs(self, wsSocket):
        #print('registerWs')
        self.socket_list.append(wsSocket)

    def unregisterWs(self, wsSocket):
        #print('unregisterWs')
        self.socket_list.remove(wsSocket)

    def send_message(self, action, data):
        for wsSocket in self.socket_list:
            wsSocket.send_message(action, data)

    def new_fuzz_job(self, ident, fuzzer, sut, cost, batch):
        self.send_message('new_fuzz_job', dict(ident=ident, fuzzer=fuzzer, sut=sut, cost=cost, batch=batch))

    def job_progress(self, ident, progress):
        self.send_message('job_progress', dict(ident=ident, progress=progress))

    def remove_job(self, ident):
        self.send_message('remove_job', dict(ident=ident))

    def job_progress(self, ident, progress):
        self.send_message('job_progress', dict(ident=ident, progress=progress))

    def activate_job(self, ident):
        self.send_message('activate_job', dict(ident=ident))

    # TODO: use with websocket
    ''' def new_issue(self, issue):
        print('WS SEND: new_issues')
        self.send_message('new_issue', issue)
    '''

    def process_loop(self):
        print('qsize: {size}'.format(size=self.events.qsize()))
        while True:
            try:
                event = self.events.get_nowait()
                if hasattr(self, event['fn']):
                    getattr(self, event['fn'])(**event['kwargs'])
            except:
                break
# print('process_loop')

def execute(args=None, parser=None):
    parser = build_parser(parent=parser)
    arguments = parser.parse_args(args)
    process_args(arguments)
    #print(arguments.config['fuzzinator.wui']['template_dir'])

    port = int(config_get_with_writeback(arguments.config, 'fuzzinator.wui', 'port', '8080'))
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
    iolcb =ioloop.PeriodicCallback(wui.process_loop, 1000)

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
