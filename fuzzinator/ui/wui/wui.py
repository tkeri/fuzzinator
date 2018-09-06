#! /usr/bin/python3

#TODO: add license

# Utility libraries
import os
import signal

from multiprocessing import Process

# Webserver stuff
from tornado import websocket, web, ioloop
from tornado.options import define, options

# Fuzzinator stuff
from fuzzinator import Controller
from fuzzinator.ui import build_parser, process_args
from .wui_listener import WuiListener


# TODO: move to fuzzinator
define('port', default=8080, help='Run on the given port.', type=int)

# TODO: test print
import json

# route to index.html
class IndexHandler(web.RequestHandler):

    def __init__(self, *args, **kwargs):
        self.db = kwargs.pop('db')
        super(IndexHandler, self).__init__(*args, **kwargs)

    def get(self):
        issues = self.db.all_issues()
        print(issues[0].keys())
        for key, value in issues[0].items():
            print(key, type(value))
            if isinstance(value, dict):
                print ("--> ", value.items())
        print(str(issues[0]['_id']))
        self.render('index.html', issues=self.db.all_issues())

# TODO(tkeri): check debug; now 'settings' is unused

class Wui(object):

    def __init__(self, controller, settings):
        self.app = web.Application([
                    (r'/', IndexHandler, dict(db=controller.db)),
                ], **settings)
        self.app.listen(options.port)

    def new_fuzz_job(self, ident, fuzzer):
        pass

def execute(args=None, parser=None):
    parser = build_parser(parent=parser)
    arguments = parser.parse_args(args)
    process_args(arguments)

    settings = dict(
        template_path = os.path.join(os.path.dirname(__file__), 'templates'),
        static_path = os.path.join(os.path.dirname(__file__), 'static'),
        debug=True
    )

    controller = Controller(config=arguments.config)
    wui = Wui(controller, settings)
    controller.listener += WuiListener()
    fuzz_process = Process(target=controller.run, args=())

    iol = ioloop.IOLoop.instance()

    try:
        iol.start()
    except KeyboardInterrupt:
        pass
    except Exception:
        os.kill(fuzz_process.pid, signal.SIGINT)
    else:
        os.kill(fuzz_process.pid, signal.SIGINT)
    finally:
        iol.add_callback(iol.stop)

