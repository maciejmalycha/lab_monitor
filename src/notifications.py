import xmpp

class Hangouts:
    def __init__(self, **config):
        self.recipient = config['recipient']
        self.sender = config['sender']
        self.password = config['password']

        self.jid = xmpp.protocol.JID(self.sender)
        self.cl = xmpp.Client(self.jid.getDomain(),debug=[])
        self.cl.connect()
        self.cl.auth(self.jid.getNode(), self.password)

    def send(self, message):
        self.cl.sendInitPresence() 
        self.cl.send(xmpp.protocol.Message(self.recipient, message, typ='chat'))
