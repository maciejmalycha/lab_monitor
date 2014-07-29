import gevent, gevent.queue
import json

class EventStream:
    """This class allows pushing notifications to the browser via Server Sent Events"""

    def __init__(self):
        self.subscriptions = []

    def write(self, msg):
        if type(msg) is not str:
            msg = json.dumps(msg)

        try:
            for sub in self.subscriptions[:]:
                sub.put(msg)
        except:
            pass

    def encode(self, string):
        return "\n".join(["data: {0}".format(line) for line in string.splitlines()])+"\n\n"

    def subscribe(self):
        q = gevent.queue.Queue()
        self.subscriptions.append(q)
        try:
            while True:
                result = q.get()
                yield self.encode(result)
        except:
            self.subscriptions.remove(q)
