import asyncio
from configparser import ConfigParser
from unittest.mock import Mock

import pygame
import pytest

from padrelay.client import client_app
from padrelay.client.input import GamepadInput
from padrelay.core.controller_state import InputState
from padrelay.protocol.constants import PROTOCOL_VERSION
from padrelay.protocol.tcp import TCPProtocolHandler
from padrelay.security import tls_utils
from padrelay.server import server_app
from padrelay.server.input_processor import GamepadHandler

from .test_controller_input import hardware as hardware
from .test_network_e2e import PASSWORD, RecordingGamepad, address, running_server


async def until(predicate):
    while not predicate():
        await asyncio.sleep(0.005)


@pytest.mark.asyncio
async def test_watchdog_retries_native_reset_failure_and_remains_active(caplog):
    server = server_app.VirtualGamepadServer.__new__(server_app.VirtualGamepadServer)
    server.shutdown_event = asyncio.Event()
    gamepad = Mock()
    handler = GamepadHandler(gamepad)
    server.gamepad_handler = handler
    handler.process(InputState(frozenset({"a"})).to_message())
    handler.last_received -= 2
    gamepad.reset_gamepad_state.side_effect = [
        OSError("native failure"),
        OSError("still unavailable"),
        None,
    ]
    task = asyncio.create_task(server._watch_input())
    try:
        await asyncio.wait_for(until(lambda: handler.last_received is None), 1)
        assert not task.done()
        assert gamepad.reset_gamepad_state.call_count == 3
        assert caplog.text.count("Input watchdog reset failed") == 1
        handler.process(InputState(frozenset({"b"})).to_message())
        handler.last_received -= 2
        gamepad.reset_gamepad_state.side_effect = None
        await asyncio.wait_for(until(lambda: handler.last_received is None), 1)
        assert gamepad.reset_gamepad_state.call_count == 4
    finally:
        server.shutdown_event.set()
        await asyncio.wait_for(task, 1)


@pytest.mark.asyncio
async def test_disconnect_reset_failure_releases_client_and_retries(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    config = ConfigParser()
    config["server"] = {"input_timeout": "0.1"}
    async with running_server(config=config) as server:
        client = client_app.VirtualGamepadClient(
            *address(server), "tcp", Mock(), password=PASSWORD
        )
        reader, writer = await asyncio.open_connection(*address(server))
        channel = TCPProtocolHandler(reader, writer)
        assert await client._tcp_auth(channel)
        assert await channel.send_message(InputState(frozenset({"a"})).to_message())
        await channel.drain()
        await asyncio.wait_for(server.virtual_gamepad.updated.wait(), 1)
        reset = Mock(side_effect=[OSError("native failure"), None])
        monkeypatch.setattr(server.virtual_gamepad, "reset_gamepad_state", reset)
        channel.close()
        await channel.wait_closed()
        await asyncio.wait_for(
            until(lambda: server.gamepad_handler.last_received is None), 1
        )
        assert not server.client_tasks and not server.active_clients
        assert reset.call_count == 2
        reset.side_effect = None
        reader, writer = await asyncio.open_connection(*address(server))
        channel = TCPProtocolHandler(reader, writer)
        try:
            assert await client._tcp_auth(channel)
        finally:
            channel.close()
            await channel.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_device_loss_reset_and_reconnect_on_new_index(
    hardware, monkeypatch, protocol
):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    monkeypatch.setattr(client_app, "RECONNECT_DELAY", 0.01)
    hardware.controller.buttons.add(pygame.CONTROLLER_BUTTON_A)
    reader = GamepadInput()
    assert reader.initialize()
    async with running_server(protocol=protocol) as server:
        client = client_app.VirtualGamepadClient(
            *address(server),
            protocol,
            reader,
            password=PASSWORD,
            ca_path=tls_utils.DEFAULT_CERT_FILE if protocol == "udp" else None,
        )
        task = asyncio.create_task(client.run())
        try:
            await asyncio.wait_for(server.virtual_gamepad.updated.wait(), 2)
            assert server.virtual_gamepad.frames[-1]["buttons"] == {"a"}
            hardware.controller.attached.return_value = False
            hardware.devices.clear()
            await asyncio.wait_for(
                until(
                    lambda: server.virtual_gamepad.resets >= 1 and not client.connected
                ),
                1,
            )
            other = Mock(wraps=hardware.joystick)
            other.get_guid.return_value = "other-guid"
            other.get_name.return_value = "Other controller"
            hardware.devices[:] = [other, hardware.joystick]
            hardware.controller.attached.return_value = True
            hardware.controller.buttons = {pygame.CONTROLLER_BUTTON_B}
            hardware.clock[0] += 1
            await asyncio.wait_for(
                until(lambda: server.virtual_gamepad.frames[-1]["buttons"] == {"b"}), 2
            )
            assert hardware.factory.call_count == 2
        finally:
            await client.shutdown()
            await asyncio.wait_for(task, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_heartbeat_does_not_keep_stale_input_alive(monkeypatch, protocol):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    config = ConfigParser()
    config["server"] = {"input_timeout": "0.1"}
    async with running_server(protocol=protocol, config=config) as server:
        client = client_app.VirtualGamepadClient(
            *address(server),
            protocol,
            Mock(),
            password=PASSWORD,
            ca_path=tls_utils.DEFAULT_CERT_FILE if protocol == "udp" else None,
        )
        reader, writer = await asyncio.open_connection(
            *address(server),
            ssl=client.ssl_context,
            server_hostname="localhost" if client.ssl_context else None,
        )
        channel = TCPProtocolHandler(reader, writer)
        transport = None
        try:
            assert await client._tcp_auth(channel)
            if protocol == "udp":
                (
                    transport,
                    _,
                ) = await asyncio.get_running_loop().create_datagram_endpoint(
                    asyncio.DatagramProtocol, remote_addr=address(server)
                )

            async def send_state():
                packet = InputState(frozenset({"a"})).to_message()
                if transport:
                    transport.sendto(client.udp_session.encode(packet))
                else:
                    assert await channel.send_message(packet)
                    await channel.drain()

            await send_state()
            await asyncio.wait_for(server.virtual_gamepad.updated.wait(), 1)
            for _ in range(4):
                assert await channel.send_message(
                    dict(type="heartbeat", protocol_version=PROTOCOL_VERSION)
                )
                await channel.drain()
                assert (await asyncio.wait_for(channel.read_message(), 1))[
                    "type"
                ] == "heartbeat_ack"
                await asyncio.sleep(0.05)
            assert server.virtual_gamepad.resets == 1
            assert not writer.is_closing()
            await send_state()
            await asyncio.wait_for(
                until(lambda: len(server.virtual_gamepad.frames) == 2), 1
            )
        finally:
            if transport:
                transport.close()
            channel.close()
            await channel.wait_closed()
