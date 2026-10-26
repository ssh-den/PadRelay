"""Repeatable protocol stress scenarios; no hardware or timing-based FPS assertions."""

import asyncio
import json
import socket
import struct
import time
from unittest.mock import Mock

import pytest

from padrelay.client.client_app import VirtualGamepadClient
from padrelay.core.controller_state import InputState
from padrelay.protocol.constants import MAX_MESSAGE_SIZE
from padrelay.protocol.tcp import TCPProtocolHandler
from padrelay.protocol.udp import UDPServerProtocol
from padrelay.security import tls_utils
from padrelay.security.udp_session import UDPSession
from padrelay.server import server_app

from .test_network_e2e import PASSWORD, RecordingGamepad, address, running_server


@pytest.mark.asyncio
@pytest.mark.parametrize("tls", [False, True])
async def test_tcp_sustained_coalesced_and_fragmented_frames(
    monkeypatch, tls, record_property
):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    count = 8192
    async with running_server(enable_tls=tls) as server:
        client = VirtualGamepadClient(
            *address(server),
            "tcp",
            Mock(),
            password=PASSWORD,
            enable_tls=tls,
            ca_path=tls_utils.DEFAULT_CERT_FILE if tls else None,
        )
        reader, writer = await asyncio.open_connection(
            *address(server),
            ssl=client.ssl_context,
            server_hostname="localhost" if tls else None,
        )
        channel = TCPProtocolHandler(reader, writer)
        writer.transport.set_write_buffer_limits(high=32768, low=8192)
        peak_buffer = 0
        started = time.perf_counter()
        try:
            assert await client._tcp_auth(channel)
            for index in range(count):
                packet = InputState(
                    frozenset({"a"}) if index % 2 else frozenset(),
                    left_x=index / (count - 1),
                ).to_message()
                data = json.dumps(packet, separators=(",", ":")).encode()
                frame = struct.pack(">I", len(data)) + data
                # Exercise boundaries inside the length prefix and payload.
                if index % 127 == 0:
                    for piece in (frame[:1], frame[1:3], frame[3:11], frame[11:]):
                        writer.write(piece)
                        await writer.drain()
                        await asyncio.sleep(0)
                else:
                    writer.write(frame)
                peak_buffer = max(peak_buffer, writer.transport.get_write_buffer_size())
                if index % 64 == 0:
                    await writer.drain()
                    await asyncio.sleep(0)
            await writer.drain()

            async def received():
                while len(server.virtual_gamepad.frames) < count:
                    await server.virtual_gamepad.updated.wait()
                    server.virtual_gamepad.updated.clear()

            await asyncio.wait_for(received(), 15)
            frames = server.virtual_gamepad.frames
            assert len(frames) == count
            assert all(
                frame["left"][0] == i / (count - 1) for i, frame in enumerate(frames)
            )
            assert frames[-1]["buttons"] == {"a"}
            assert peak_buffer <= 32768 + 64 * MAX_MESSAGE_SIZE
            elapsed = time.perf_counter() - started
            record_property("frames", count)
            record_property("seconds", elapsed)
            record_property("peak_write_buffer_bytes", peak_buffer)
            print(
                f"TCP tls={tls}: {count} frames in {elapsed:.3f}s; peak write buffer={peak_buffer} bytes"
            )
        finally:
            channel.close()
            await channel.wait_closed()


class CountInput:
    def __init__(self):
        self.count = 0
        self.last = None

    def process(self, message):
        self.last = InputState.from_message(message)
        self.count += 1


def test_udp_authenticated_reordering_replay_and_forgery_under_load(record_property):
    count = 20000
    receiving = UDPSession.create("127.0.0.1")
    sending = UDPSession.from_parameters(receiving.parameters())
    output = CountInput()
    protocol = UDPServerProtocol(output, {receiving.session_id: receiving})
    protocol.connection_made(Mock())
    started = time.perf_counter()
    for index in range(0, count, 2):
        old = sending.encode(InputState(left_x=index / count).to_message())
        new = sending.encode(InputState(left_x=(index + 1) / count).to_message())
        forged = bytearray(new)
        forged[-1] ^= 0x80
        protocol.datagram_received(bytes(forged), ("127.0.0.1", 1))
        protocol.datagram_received(new, ("192.0.2.1", 1))
        protocol.datagram_received(new, ("127.0.0.1", 1))
        protocol.datagram_received(old, ("127.0.0.1", 2))
        protocol.datagram_received(new, ("127.0.0.1", 3))
    elapsed = time.perf_counter() - started
    assert (
        output.count == count // 2
    )  # Older authenticated states never overwrite newer ones.
    assert output.last.left_x == (count - 1) / count
    assert receiving.highest_received == count - 1
    assert receiving.received_bitmap.bit_length() <= 64
    assert len(protocol.sessions) == 1
    record_property("encrypted_frames", count)
    record_property("datagrams", count // 2 * 5)
    record_property("seconds", elapsed)
    print(
        f"UDP crypto: {count} encrypted frames / {count // 2 * 5} datagrams in {elapsed:.3f}s; replay window <=64 bits"
    )


@pytest.mark.asyncio
async def test_udp_real_socket_burst_and_final_state(monkeypatch, record_property):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    count = 4096
    async with running_server(protocol="udp", max_requests=100000) as server:
        client = VirtualGamepadClient(
            *address(server),
            "udp",
            Mock(),
            password=PASSWORD,
            ca_path=tls_utils.DEFAULT_CERT_FILE,
        )
        reader, writer = await asyncio.open_connection(
            *address(server), ssl=client.ssl_context, server_hostname="localhost"
        )
        channel = TCPProtocolHandler(reader, writer)
        transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            asyncio.DatagramProtocol, remote_addr=address(server)
        )
        try:
            assert await client._tcp_auth(channel)
            session = client.udp_session
            started = time.perf_counter()
            for index in range(count):
                transport.sendto(
                    session.encode(InputState(left_x=index / count).to_message())
                )
                if index % 16 == 0:
                    await asyncio.sleep(0.001)
            await asyncio.sleep(0.05)
            received_burst = len(server.virtual_gamepad.frames)
            # UDP permits loss. Fresh final snapshots must converge, not replay an old state.
            for _ in range(100):
                transport.sendto(session.encode(InputState(left_x=1.0).to_message()))
                await asyncio.sleep(0.01)
                if (
                    server.virtual_gamepad.frames
                    and server.virtual_gamepad.frames[-1]["left"][0] == 1
                ):
                    break
            assert server.virtual_gamepad.frames[-1]["left"][0] == 1
            assert 0 < received_burst <= count
            record_property("sent_burst", count)
            record_property("received_burst", received_burst)
            record_property("seconds", time.perf_counter() - started)
            print(
                f"UDP socket: sent={count}, accepted={received_burst}; final state converged"
            )
        finally:
            transport.close()
            channel.close()
            await channel.wait_closed()


@pytest.mark.asyncio
async def test_outbound_size_limit_is_enforced():
    writer = Mock()
    assert not await TCPProtocolHandler(writer=writer).send_message(
        b"x" * (MAX_MESSAGE_SIZE + 1)
    )
    writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_tcp_backpressure_bounds_queue_until_slow_peer_reads(record_property):
    gate = asyncio.Event()
    received = asyncio.Event()
    count = 2048
    max_buffer = 0
    completed = 0

    async def consume(reader, writer):
        try:
            await gate.wait()
            handler = TCPProtocolHandler(reader)
            for _ in range(count):
                assert (
                    InputState.from_message(await handler.read_message())
                    == InputState()
                )
            received.set()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(consume, "127.0.0.1", 0, limit=4096)
    reader, writer = await asyncio.open_connection(*server.sockets[0].getsockname())
    writer.get_extra_info("socket").setsockopt(
        socket.SOL_SOCKET, socket.SO_SNDBUF, 4096
    )
    writer.transport.set_write_buffer_limits(high=8192, low=4096)
    channel = TCPProtocolHandler(reader, writer)

    async def produce():
        nonlocal max_buffer, completed
        for _ in range(count):
            assert await channel.send_message(InputState().to_message())
            max_buffer = max(max_buffer, writer.transport.get_write_buffer_size())
            assert await channel.drain()
            completed += 1

    task = asyncio.create_task(produce())
    try:
        await asyncio.sleep(0.05)
        assert not task.done() and completed < count
        assert max_buffer <= 8192 + MAX_MESSAGE_SIZE
        gate.set()
        await asyncio.wait_for(task, 15)
        await asyncio.wait_for(received.wait(), 2)
        record_property("frames", count)
        record_property("peak_write_buffer_bytes", max_buffer)
        print(
            f"TCP slow peer: {count} frames; queue bounded at {max_buffer} bytes; resumed after peer read"
        )
    finally:
        gate.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        channel.close()
        await channel.wait_closed()
        server.close()
        await server.wait_closed()
