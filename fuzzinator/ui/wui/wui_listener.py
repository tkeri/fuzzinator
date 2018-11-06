import inspect

from fuzzinator.listener import EventListener


class WuiListener(EventListener):

    def __init__(self, events, lock):
        for fn, _ in inspect.getmembers(EventListener, predicate=inspect.isfunction):
            setattr(self, fn, self.Trampoline(name=fn, events=events, lock=lock))

    class Trampoline(object):
        def __init__(self, name, events, lock):
            self.name = name
            self.events = events
            self.lock = lock

        def __call__(self, **kwargs):
            with self.lock:
                try:
                    self.events.put_nowait({'fn': self.name, 'kwargs': kwargs})
                except:
                    pass
