import logging
import gevent, gevent.queue
import json

class SSEHandler(logging.Handler):
    """This class allows logging to a Server Sent Event stream"""

    def __init__(self):
        logging.Handler.__init__(self)        
        self.subscriptions = []

    def emit(self, record):
        try:
            msg = json.dumps({
                'time': record.created,
                'level': record.levelname,
                'message': self.format(record),
            })

            try:
                for sub in self.subscriptions[:]:
                    sub.put(msg)
            except:
                pass

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
        

    def subscribe(self):
        q = gevent.queue.Queue()
        self.subscriptions.append(q)
        try:
            while True:
                result = q.get()
                yield "data: %s\n\n"%result
        except:
            self.subscriptions.remove(q)
