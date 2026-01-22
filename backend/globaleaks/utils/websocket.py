import json
from autobahn.twisted.websocket import WebSocketServerProtocol
from twisted.internet import reactor
from globaleaks.sessions import Sessions

CLIENTS = set()

class WebSocketServerProtocol(WebSocketServerProtocol):
    def connectionMade(self):
        self._connectionMade()

    def onOpen(self):
        self.user_id = None
        self.tip_ids = set()
        self.session = None
        CLIENTS.add(self)

    def onClose(self, wasClean, code, reason):
        CLIENTS.discard(self)
        self.user_id = None
        self.tip_ids = set()
        self.session = None

    def onMessage(self, payload, isBinary):
        try:
            data = json.loads(payload.decode("utf-8"))
        except:
            self.sendClose(code=4000, reason="Invalid JSON")
            return

        if data.get("type") == "auth":
            session_id = data.get("session_id")
            tip_ids = data.get("tip_ids", [])

            if not session_id:
                self.sendClose(code=4001, reason="Missing session_id")
                return

            session = Sessions.get(session_id)

            if not session:
                self.sendClose(code=4002, reason="Invalid session")
                return

            self.session = session
            self.user_id = session.user_id
            self.tip_ids = set(tip_ids)

            self.send_update({"type": "auth_ok"})

    def send_update(self, payload):
        self.sendMessage(json.dumps(payload).encode("utf-8"))


def notify_users(payload, tip_id=None, user_ids=None, exclude_user=None):
    def send():
        for client in CLIENTS:
            if not client.session:
                continue

            if user_ids and client.user_id not in user_ids:
                continue

            if tip_id and tip_id not in client.tip_ids:
                continue

            if exclude_user and client.user_id == exclude_user:
                continue

            client.send_update(payload)

    reactor.callFromThread(send)
