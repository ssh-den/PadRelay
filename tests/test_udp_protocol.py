import json
from types import SimpleNamespace

import time
from padrelay.protocol.udp import UDPServerProtocol
from padrelay.security.auth import Authenticator
from padrelay.protocol.constants import PROTOCOL_VERSION


class DummyTransport:
    def __init__(self):
        self.sent = []

    def get_extra_info(self, name):
        if name == 'sockname':
            return ('127.0.0.1', 0)
        return None

    def sendto(self, data, addr):
        self.sent.append((json.loads(data.decode()), addr))

    def close(self):
        pass


class DummyHandler:
    def __init__(self):
        self.received = []

    def process(self, msg):
        self.received.append(msg)


def test_udp_heartbeat_and_input(monkeypatch):
    auth = Authenticator('key')
    handler = DummyHandler()
    proto = UDPServerProtocol(handler, auth)
    transport = DummyTransport()
    proto.connection_made(transport)
    addr = ('127.0.0.1', 1234)

    monkeypatch.setattr(time, 'time', lambda: 1000)
    token = auth.generate_udp_token()
    heartbeat = {
        'type': 'heartbeat',
        'protocol_version': PROTOCOL_VERSION,
        'auth_token': token,
    }
    proto.datagram_received(json.dumps(heartbeat).encode(), addr)
    assert transport.sent[0][0]['type'] == 'heartbeat_ack'

    input_msg = {
        'type': 'input',
        'protocol_version': PROTOCOL_VERSION,
        'auth_token': token,
        'buttons': [True],
        'axes': [0.0, 0.0],
    }
    proto.datagram_received(json.dumps(input_msg).encode(), addr)
    assert handler.received[0]['type'] == 'input'


def test_udp_auth_params_request(monkeypatch):
    hashed = Authenticator.hash_password('pw', iterations=120000)
    server_auth = Authenticator(hashed)
    handler = DummyHandler()
    proto = UDPServerProtocol(handler, server_auth)
    transport = DummyTransport()
    proto.connection_made(transport)
    addr = ('127.0.0.1', 5678)

    req = {
        'type': 'auth_params_request',
        'protocol_version': PROTOCOL_VERSION,
    }
    proto.datagram_received(json.dumps(req).encode(), addr)
    resp = transport.sent[0][0]
    assert resp['type'] == 'auth_params'
    assert resp['salt'] == server_auth.salt
    assert resp['iterations'] == server_auth.iterations

    client_auth = Authenticator('pw')
    client_auth.set_parameters(resp['salt'], resp['iterations'])
    client_auth.password_plain = None
    monkeypatch.setattr(time, 'time', lambda: 2000)
    token = client_auth.generate_udp_token()
    heartbeat = {
        'type': 'heartbeat',
        'protocol_version': PROTOCOL_VERSION,
        'auth_token': token,
    }
    proto.datagram_received(json.dumps(heartbeat).encode(), addr)
    assert transport.sent[1][0]['type'] == 'heartbeat_ack'
