"""Async integration tests for TCP and UDP communication"""

import asyncio
import contextlib
import pytest

from padrelay.protocol.constants import PROTOCOL_VERSION
from padrelay.client import client_app
from padrelay.server import server_app
from padrelay.security.auth import Authenticator


class DummyGamepadDevice:
    def __init__(self):
        self.updated = 0
        self.reset_called = 0
        self.pressed = []

    def reset(self):
        self.reset_called += 1

    def update(self):
        self.updated += 1

    def press_button(self, button):
        self.pressed.append(("press", button))

    def release_button(self, button):
        self.pressed.append(("release", button))

    def left_joystick_float(self, **kwargs):
        pass

    def right_joystick_float(self, **kwargs):
        pass

    def left_trigger_float(self, **kwargs):
        pass

    def right_trigger_float(self, **kwargs):
        pass


class DummyVirtualGamepad:
    def __init__(self, gamepad_type="xbox360", config=None):
        self.gamepad_type = gamepad_type
        self.gamepad = DummyGamepadDevice()
        self.button_mapping = {0: 1}

    def get_button_mapping(self):
        return self.button_mapping

    def reset_gamepad_state(self):
        self.gamepad.reset()

    def press_button(self, *args, **kwargs):
        self.gamepad.press_button(*args, **kwargs)

    def release_button(self, *args, **kwargs):
        self.gamepad.release_button(*args, **kwargs)

    def left_joystick_float(self, *args, **kwargs):
        self.gamepad.left_joystick_float(*args, **kwargs)

    def right_joystick_float(self, *args, **kwargs):
        self.gamepad.right_joystick_float(*args, **kwargs)

    def left_trigger_float(self, *args, **kwargs):
        self.gamepad.left_trigger_float(*args, **kwargs)

    def right_trigger_float(self, *args, **kwargs):
        self.gamepad.right_trigger_float(*args, **kwargs)

    def update(self):
        self.gamepad.update()


class DummyGamepadInput:
    def __init__(self):
        self.polled = 0
        self.cleanup_called = False

    def poll(self):
        self.polled += 1
        if self.polled > 1:
            return None
        return {
            "type": "input",
            "protocol_version": PROTOCOL_VERSION,
            "timestamp": "now",
            "buttons": [True],
            "axes": [0.0, 0.0],
            "hats": [],
        }

    def cleanup(self):
        self.cleanup_called = True


async def run_server_client(protocol: str):
    """Start server and client with the given protocol and return them."""
    server = server_app.VirtualGamepadServer(
        "127.0.0.1", 0, password="secret", protocol=protocol
    )
    server_task = asyncio.create_task(server.run())

    # Wait for server to start
    while protocol == "tcp" and not server.server:
        await asyncio.sleep(0.01)
    while protocol == "udp" and not getattr(server, "transport", None):
        await asyncio.sleep(0.01)

    if protocol == "tcp":
        host, port = server.server.sockets[0].getsockname()
    else:
        host, port = server.transport.get_extra_info("sockname")

    gamepad = DummyGamepadInput()
    client = client_app.VirtualGamepadClient(
        host, port, protocol, gamepad, update_rate=30, password="secret"
    )
    client_task = asyncio.create_task(client.run())

    await asyncio.sleep(0.3)

    await client.shutdown()
    await server.shutdown()

    await asyncio.gather(client_task, return_exceptions=True)
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task

    return gamepad, server.virtual_gamepad


@pytest.mark.asyncio
async def test_tcp_end_to_end(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    gamepad, vpad = await run_server_client("tcp")
    assert gamepad.polled > 0
    assert vpad.gamepad.updated > 0
    assert gamepad.cleanup_called


@pytest.mark.asyncio
async def test_udp_end_to_end(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    gamepad, vpad = await run_server_client("udp")
    assert gamepad.polled > 0
    assert vpad.gamepad.updated > 0
    assert gamepad.cleanup_called


@pytest.mark.asyncio
async def test_udp_end_to_end_hashed(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    hashed = Authenticator.hash_password("secret")
    server = server_app.VirtualGamepadServer(
        "127.0.0.1", 0, password=hashed, protocol="udp"
    )
    server_task = asyncio.create_task(server.run())

    while not getattr(server, "transport", None):
        await asyncio.sleep(0.01)

    host, port = server.transport.get_extra_info("sockname")

    gamepad = DummyGamepadInput()
    client = client_app.VirtualGamepadClient(
        host, port, "udp", gamepad, update_rate=30, password=hashed
    )
    client_task = asyncio.create_task(client.run())

    await asyncio.sleep(0.3)

    await client.shutdown()
    await server.shutdown()

    await asyncio.gather(client_task, return_exceptions=True)
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task

    assert gamepad.polled > 0
    assert gamepad.cleanup_called


@pytest.mark.asyncio
async def test_udp_plain_client_hashed_server(monkeypatch):
    """Client with plaintext password should obtain parameters and authenticate"""
    monkeypatch.setattr(server_app, "VirtualGamepad", DummyVirtualGamepad)
    hashed = Authenticator.hash_password("secret")
    server = server_app.VirtualGamepadServer(
        "127.0.0.1", 0, password=hashed, protocol="udp"
    )
    server_task = asyncio.create_task(server.run())

    while not getattr(server, "transport", None):
        await asyncio.sleep(0.01)

    host, port = server.transport.get_extra_info("sockname")

    gamepad = DummyGamepadInput()
    client = client_app.VirtualGamepadClient(
        host, port, "udp", gamepad, update_rate=30, password="secret"
    )
    client_task = asyncio.create_task(client.run())

    await asyncio.sleep(0.3)

    await client.shutdown()
    await server.shutdown()

    await asyncio.gather(client_task, return_exceptions=True)
    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await server_task

    assert gamepad.polled > 0
    assert gamepad.cleanup_called
