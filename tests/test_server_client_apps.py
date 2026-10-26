import asyncio
import contextlib
import pytest

from padrelay.server import server_app
from padrelay.client import client_app
from padrelay.protocol.tcp import TCPProtocolHandler


class DummyGamepadInput:
    def __init__(self):
        self.cleaned = False

    def poll(self):
        return {
            "type": "input",
            "protocol_version": "1.0",
            "buttons": [],
            "axes": [],
            "hats": [],
        }

    def cleanup(self):
        self.cleaned = True


class DummyVirtualGamepad:
    def __init__(self, *a, **k):
        self.reset_called = False

    def reset_gamepad_state(self):
        self.reset_called = True

    def get_button_mapping(self):
        return {}


class DummyGamepadHandler:
    def __init__(self, *a, **k):
        self.received = []

    def process(self, msg):
        self.received.append(msg)


@pytest.mark.asyncio
async def test_tcp_connection_limit(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    monkeypatch.setattr(server_app, "GamepadHandler", DummyGamepadHandler)

    server = server_app.VirtualGamepadServer("127.0.0.1", 0, password=None)
    server_task = asyncio.create_task(server._run_tcp_server())

    while not server.server:
        await asyncio.sleep(0.01)

    host, port = server.server.sockets[0].getsockname()

    # First connection should succeed and stay open
    r1, w1 = await asyncio.open_connection(host, port)
    handler1 = TCPProtocolHandler(r1, w1)
    await handler1.send_message({"type": "noop"})
    await handler1.drain()

    # Second connection should be rejected due to limit
    r2, w2 = await asyncio.open_connection(host, port)
    handler2 = TCPProtocolHandler(r2, w2)
    msg = await handler2.read_message()
    assert msg["type"] == "error"
    assert "Another client" in msg["message"]
    w2.close()
    await w2.wait_closed()

    w1.close()
    await w1.wait_closed()
    await server.shutdown()
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task


@pytest.mark.asyncio
async def test_tcp_auth_failure(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    monkeypatch.setattr(server_app, "GamepadHandler", DummyGamepadHandler)

    server = server_app.VirtualGamepadServer("127.0.0.1", 0, password="pw")
    server_task = asyncio.create_task(server._run_tcp_server())

    while not server.server:
        await asyncio.sleep(0.01)
    host, port = server.server.sockets[0].getsockname()

    reader, writer = await asyncio.open_connection(host, port)
    handler = TCPProtocolHandler(reader, writer)
    challenge = await handler.read_message()
    assert challenge["type"] == "auth_challenge"
    await handler.send_message({
        "type": "auth_response",
        "protocol_version": "1.0",
        "response": "bad"
    })
    await handler.drain()
    result = await handler.read_message()
    assert result["type"] == "auth_failed"
    writer.close()
    await writer.wait_closed()

    await server.shutdown()
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task


@pytest.mark.asyncio
async def test_client_auth_version_mismatch(monkeypatch):
    async def fake_server(reader, writer):
        handler = TCPProtocolHandler(reader, writer)
        await handler.send_message({
            "type": "auth_challenge",
            "protocol_version": "0.9",
            "challenge": "x"
        })
        await handler.drain()
        await handler.read_message()
        writer.close()

    srv = await asyncio.start_server(fake_server, "127.0.0.1", 0)
    host, port = srv.sockets[0].getsockname()
    client = client_app.VirtualGamepadClient(host, port, "tcp", DummyGamepadInput(), password="pw")

    reader, writer = await asyncio.open_connection(host, port)
    handler = TCPProtocolHandler(reader, writer)
    result = await client._tcp_auth(handler)
    assert result is False
    writer.close()
    await writer.wait_closed()
    srv.close()
    await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_heartbeat_timeout(monkeypatch):
    async def fake_server(reader, writer):
        handler = TCPProtocolHandler(reader, writer)
        await handler.read_message()  # heartbeat
        await asyncio.sleep(0.2)
        writer.close()

    srv = await asyncio.start_server(fake_server, "127.0.0.1", 0)
    host, port = srv.sockets[0].getsockname()
    client = client_app.VirtualGamepadClient(host, port, "tcp", DummyGamepadInput(), password="pw")

    reader, writer = await asyncio.open_connection(host, port)
    handler = TCPProtocolHandler(reader, writer)
    res = await client._tcp_heartbeat_loop(handler, interval=0.05)
    assert res is False
    writer.close()
    await writer.wait_closed()
    srv.close()
    await srv.wait_closed()

@pytest.mark.asyncio
async def test_run_tcp_server_port_in_use(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    monkeypatch.setattr(server_app, "GamepadHandler", DummyGamepadHandler)

    busy = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    host, port = busy.sockets[0].getsockname()
    server = server_app.VirtualGamepadServer(host, port, password=None)

    with pytest.raises(OSError):
        await server._run_tcp_server()

    busy.close()
    await busy.wait_closed()
