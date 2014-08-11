import json

class EventStream:
    """This class allows pushing notifications to the browser via Server Sent Events"""

    def __init__(self, red, rkey):
        self.red = red
        self.rkey = rkey

    def encode(self, string):
        """Encodes string so that it can be sent as SSE"""
        if type(string) is not str:
            string = json.dumps(string) 
        return "\n".join(["data: {0}".format(line) for line in string.splitlines()])+"\n\n"

    def subscribe(self):
        """Yields messages whenever pubsub receives them"""
        pubsub = self.red.pubsub()
        pubsub.subscribe(self.rkey)
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield self.encode(message['data'])
        except:
            pubsub.unsubscribe()
            raise StopIteration