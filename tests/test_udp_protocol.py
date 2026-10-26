"""UDP v2 rejects forgery/replay and never answers unauthenticated datagrams."""

import json
from unittest.mock import Mock

import pytest

from padrelay.protocol.udp import UDPServerProtocol
from padrelay.security.udp_session import UDPSession

IP = "127.0.0.1"
MESSAGE = {"type": "input", "protocol_version": "1.0", "buttons": [True], "axes": [0.5]}


@pytest.fixture
def channel():
    server = UDPSession.create(IP)
    client = UDPSession.from_parameters(server.parameters())
    handler, transport = Mock(), Mock()
    protocol = UDPServerProtocol(handler, {server.session_id: server})
    protocol.connection_made(transport)
    return server, client, protocol, handler, transport


def test_encrypted_input_and_replay(channel):
    _, client, protocol, handler, transport = channel
    packet = client.encode(MESSAGE)
    assert b"buttons" not in packet
    protocol.datagram_received(packet, (IP, 1234))
    handler.process.assert_called_once_with(MESSAGE)
    protocol.datagram_received(packet, (IP, 5678))
    handler.process.assert_called_once()
    transport.sendto.assert_not_called()


@pytest.mark.parametrize("offset", [0, 4, 20, 27, 28, -1])
def test_tampering_cannot_advance_replay_state(channel, offset):
    server, client, protocol, handler, _ = channel
    packet = client.encode(MESSAGE)
    forged = bytearray(packet)
    forged[offset] ^= 0x80
    protocol.datagram_received(bytes(forged), (IP, 1))
    assert server.highest_received == -1
    handler.process.assert_not_called()
    protocol.datagram_received(packet, (IP, 1))
    handler.process.assert_called_once_with(MESSAGE)


def test_wrong_source_ip_and_unknown_or_retired_session(channel):
    server, client, protocol, handler, _ = channel
    packet = client.encode(MESSAGE)
    protocol.datagram_received(packet, ("192.0.2.1", 1))
    assert server.highest_received == -1
    protocol.sessions.clear()
    protocol.datagram_received(packet, (IP, 1))
    handler.process.assert_not_called()


def test_old_key_cannot_authenticate_new_session(channel):
    _, client, protocol, handler, _ = channel
    new = UDPSession.create(IP)
    protocol.sessions = {new.session_id: new}
    protocol.datagram_received(client.encode(MESSAGE), (IP, 1))
    handler.process.assert_not_called()


def test_legacy_tokens_and_parameter_requests_fail_closed(channel):
    _, _, protocol, handler, transport = channel
    for message in [
        dict(MESSAGE, auth_token="captured-token"),
        {"type": "auth_params_request"},
    ]:
        protocol.datagram_received(json.dumps(message).encode(), (IP, 1))
    handler.process.assert_not_called()
    transport.sendto.assert_not_called()


def test_session_expiry(channel, monkeypatch):
    server, client, protocol, handler, _ = channel
    packet = client.encode(MESSAGE)
    monkeypatch.setattr(
        "padrelay.security.udp_session.time.monotonic", lambda: server.expires_at + 1
    )
    protocol.datagram_received(packet, (IP, 1))
    handler.process.assert_not_called()
    with pytest.raises(ValueError):
        client.encode(MESSAGE)


def test_nonce_exhaustion_never_wraps(channel):
    server, client, _, _, _ = channel
    client.send_sequence = client.MAX_SEQUENCE - 1
    assert server.decode(client.encode(MESSAGE)) == MESSAGE
    with pytest.raises(ValueError):
        client.encode(MESSAGE)


def test_reordered_old_state_cannot_override_newer_input(channel):
    _, client, protocol, handler, _ = channel
    older = client.encode(MESSAGE)
    newer_message = dict(MESSAGE, buttons=[False])
    newer = client.encode(newer_message)
    protocol.datagram_received(newer, (IP, 1))
    protocol.datagram_received(older, (IP, 1))
    handler.process.assert_called_once_with(newer_message)


def test_reordered_packets_have_bounded_duplicate_detection(channel):
    server, client, _, _, _ = channel
    packets = [client.encode(MESSAGE) for _ in range(70)]
    assert server.decode(packets[69]) == MESSAGE
    assert server.decode(packets[68]) == MESSAGE
    assert server.decode(packets[68]) is None
    assert server.decode(packets[0]) is None
    assert server.received_bitmap.bit_length() <= 64
