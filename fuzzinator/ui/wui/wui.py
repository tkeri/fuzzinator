#! /usr/bin/pyton3

#TODO: add license

import os
import signal

from multiprocessing import Process
from tornado import websocket, web, ioloop
from tornado.options import define, options

from fuzzinator import Controller
from fuzzinator.ui import build_parser, process_args
from .wui_listener import WuiListener


define('port', default=8080, help='Run on the given port.', type=int)


class IndexHandler(web.RequestHandler):

    def __init__(self, *args, db, **kwargs):
        super(IndexHandler, self).__init__(*args, **kwargs)
        self.db = db

    def get(self):
        content = '<h1>Hello Fuzzinator WUI</h1><br><table>'
        for issue in self.db.all_issues():
            content += '<tr><td>' + issue['id'].decode('utf-8', 'ignore') + '</td></tr>'
        content += '</table>'
        self.write(content)


class Wui(object):

    def __init__(self, controller):
        self.app = web.Application([
                    (r'/', IndexHandler, dict(db=controller.db)),
                ])
        self.app.listen(options.port)

    def new_fuzz_job(self, ident, fuzzer):
        pass


def execute(args=None, parser=None):
    parser = build_parser(parent=parser)
    arguments = parser.parse_args(args)
    process_args(arguments)

    controller = Controller(config=arguments.config)
    wui = Wui(controller)
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

