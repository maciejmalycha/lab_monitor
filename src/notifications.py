import xmpp

class Hangouts:
    def __init__(self, **config):
        self.recipient = config['recipient']
        self.sender = config['sender']
        self.password = config['password']

        self.jid = xmpp.protocol.JID(self.sender)
        self.cl = xmpp.Client(self.jid.getDomain(),debug=[])
        self.cl.connect() or raise IOError("Cannot connect to XMPP server")
        self.cl.auth(self.jid.getNode(), self.password) or raise IOError("XMPP authentication failed")

    def send(self, message):
        if not self.cl.isConnected():
            self.cl.reconnectAndReauth()
        self.cl.sendInitPresence() 
        self.cl.send(xmpp.protocol.Message(self.recipient, message, typ='chat'))
