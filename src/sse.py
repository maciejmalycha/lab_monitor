import gevent, gevent.queue
import json

class EventStream:
    """This class allows pushing notifications to the browser via Server Sent Events"""

    def __init__(self):
        self.subscriptions = []

    def write(self, msg):
        """Pushes a message to all connected subscribers (if message is not a string, it will be JSON encoded)"""
        if type(msg) is not str:
            msg = json.dumps(msg)

        try:
            for sub in self.subscriptions[:]:
                sub.put(msg)
        except:
            pass

    def encode(self, string):
        """Encodes string so that it can be sent as SSE"""
        return "\n".join(["data: {0}".format(line) for line in string.splitlines()])+"\n\n"

    def subscribe(self):
        """Creates a new subscriber and yields messages whenever self.write is called somewhere else"""
        q = gevent.queue.Queue()
        self.subscriptions.append(q)
        try:
            while True:
                result = q.get()
                yield self.encode(result)
        except:
            self.subscriptions.remove(q)
