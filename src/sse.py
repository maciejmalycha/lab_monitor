import json

class EventStream:
    """This class allows pushing notifications to the browser via Server Sent Events"""

    def __init__(self, red, rkey):
        self.red = red
        self.rkey = rkey
        self.subs = []

    def encode(self, string):
        """Encodes string so that it can be sent as SSE"""
        if type(string) is not str:
            string = json.dumps(string) 
        return "\n".join(["data: {0}".format(line) for line in string.splitlines()])+"\n\n"

    def subscribe(self):
        """Yields messages whenever pubsub receives them"""
        pubsub = self.red.pubsub()
        pubsub.subscribe(self.rkey)
        self.subs.append(pubsub)
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield self.encode(message['data'])
                elif message['type'] == 'unsubscribe':
                    return
        except:
            pubsub.unsubscribe()
            return

    def close_all(self):
        for sub in self.subs:
            sub.unsubscribe()
