"""Malformed network payloads, connection cleanup and TLS identity file creation."""

import asyncio
import json
import struct
from unittest.mock import AsyncMock, Mock

import pytest

from padrelay.client.client_app import VirtualGamepadClient
from padrelay.protocol.constants import MAX_MESSAGE_SIZE
from padrelay.protocol.messages import validate_input_message
from padrelay.protocol.tcp import TCPProtocolHandler
from padrelay.protocol.udp import UDPServerProtocol
from padrelay.security import tls_utils


@pytest.mark.parametrize(
    "data", [b"[]", b"null", b"42", b"\xff", b"x" * (MAX_MESSAGE_SIZE + 1)]
)
def test_udp_discards_malformed_packets(data):
    handler, transport = Mock(), Mock()
    protocol = UDPServerProtocol(handler)
    protocol.connection_made(transport)
    protocol.datagram_received(data, ("127.0.0.1", 1234))
    handler.process.assert_not_called()
    transport.sendto.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [b"[]", b"null", b"42", b"\xff"])
async def test_tcp_discards_non_object_payloads(data):
    reader = asyncio.StreamReader()
    reader.feed_data(struct.pack(">I", len(data)) + data)
    reader.feed_eof()
    assert await TCPProtocolHandler(reader).read_message() is None


def test_hat_pairs_survive_json_roundtrip():
    message = {"type": "input", "buttons": [], "axes": [], "hats": [(0, 1)]}
    assert validate_input_message(json.loads(json.dumps(message)))


@pytest.mark.parametrize("field", ["hats", "triggers"])
@pytest.mark.parametrize("value", [None, False, "", 0])
def test_optional_arrays_reject_wrong_types(field, value):
    assert not validate_input_message({"type": "input", field: value})


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_tcp_connection_is_closed_on_auth_failure_or_cancellation(
    monkeypatch, cancel
):
    client = VirtualGamepadClient("127.0.0.1", 9999, "tcp", Mock())
    writer = Mock()
    writer.wait_closed = AsyncMock()
    monkeypatch.setattr(
        asyncio, "open_connection", AsyncMock(return_value=(Mock(), writer))
    )

    async def authenticate(_handler):
        client.shutdown_event.set()
        if cancel:
            raise asyncio.CancelledError
        return False

    client._tcp_auth = authenticate
    # Shutdown must bypass the normal five-second reconnect backoff.
    await asyncio.wait_for(client._run_tcp(), 0.5)
    assert not client.connected
    writer.close.assert_called()
    writer.wait_closed.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_client_shutdown_cancels_pending_connection(monkeypatch, protocol):
    client = VirtualGamepadClient(
        "127.0.0.1", 9999, protocol, Mock(), password="test-password"
    )
    connecting = asyncio.Event()

    async def connect(*_args, **_kwargs):
        connecting.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(asyncio, "open_connection", connect)
    task = asyncio.create_task(client.run())
    try:
        await asyncio.wait_for(connecting.wait(), 1)
        await asyncio.wait_for(client.shutdown(), 0.5)
        assert task.done()
        assert task.result() is True
        assert not client.running
        client.gamepad.cleanup.assert_called_once()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_stream_close_aborts_when_peer_does_not_finish_shutdown():
    writer = Mock()

    async def stalled_close():
        await asyncio.Event().wait()

    writer.wait_closed = stalled_close
    handler = TCPProtocolHandler(writer=writer)
    handler.close()
    await asyncio.wait_for(handler.wait_closed(), 1.5)
    writer.transport.abort.assert_called_once()


@pytest.mark.parametrize("existing", ["cert", "key"])
def test_certificate_generation_preserves_existing_identity(tmp_path, existing):
    cert, key = tmp_path / "server.crt", tmp_path / "server.key"
    target = cert if existing == "cert" else key
    target.write_bytes(b"existing identity")
    with pytest.raises(FileExistsError):
        tls_utils.generate_self_signed_cert(cert, key)
    assert target.read_bytes() == b"existing identity"


def test_private_key_is_created_with_owner_only_permissions(tmp_path, monkeypatch):
    original_open = tls_utils.os.open
    creations = []

    def secure_open(path, flags, mode):
        creations.append((flags, mode))
        return original_open(path, flags, mode)

    monkeypatch.setattr(tls_utils.os, "open", secure_open)
    tls_utils.generate_self_signed_cert(
        tmp_path / "server.crt", tmp_path / "server.key"
    )
    assert len(creations) == 2
    assert all(
        flags & tls_utils.os.O_EXCL and mode == 0o600 for flags, mode in creations
    )
