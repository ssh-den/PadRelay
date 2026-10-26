"""PBKDF2 work bounds, IP budgets, connection slots and TLS-owned UDP sessions."""

import asyncio
import threading
from unittest.mock import AsyncMock, Mock

import pytest

from padrelay.client.client_app import VirtualGamepadClient
from padrelay.core import config
from padrelay.protocol.tcp import TCPProtocolHandler
from padrelay.protocol.udp import UDPServerProtocol
from padrelay.security import tls_utils
from padrelay.security.auth import Authenticator
from padrelay.security.rate_limiting import ConnectionTracker
from padrelay.server import server_app
from tests.test_network_e2e import RecordingGamepad, address, running_server


@pytest.mark.parametrize(
    "iterations", [0, -1, True, "100000", 99999, 600001, 2_000_000_000, None, 1.5]
)
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_untrusted_kdf_work_rejected_before_hashing(
    monkeypatch, iterations, asynchronous
):
    auth = Authenticator("test-password")
    original = (auth.salt, auth.iterations, auth.password_hash)
    derive = Mock(side_effect=AssertionError("Untrusted work must not be scheduled"))
    monkeypatch.setattr(auth, "_hash_password", derive)
    with pytest.raises(ValueError):
        if asynchronous:
            await auth.set_parameters_async("a" * 32, iterations)
        else:
            auth.set_parameters("a" * 32, iterations)
    derive.assert_not_called()
    assert (auth.salt, auth.iterations, auth.password_hash) == original


@pytest.mark.parametrize("salt", [None, b"a" * 32, "", "a" * 15, "a" * 129, "я" * 32])
def test_untrusted_salt_rejected_atomically(monkeypatch, salt):
    auth = Authenticator("test-password")
    original = (auth.salt, auth.iterations, auth.password_hash)
    derive = Mock()
    monkeypatch.setattr(auth, "_hash_password", derive)
    with pytest.raises(ValueError):
        auth.set_parameters(salt, 100000)
    derive.assert_not_called()
    assert (auth.salt, auth.iterations, auth.password_hash) == original


@pytest.mark.parametrize("iterations", [100000, 600000])
def test_kdf_allowed_boundary(iterations):
    Authenticator.validate_parameters("a" * 32, iterations)


@pytest.mark.asyncio
async def test_kdf_does_not_block_event_loop(monkeypatch):
    auth = Authenticator("test-password")
    started, release = threading.Event(), threading.Event()

    def derive(*_args):
        assert threading.current_thread() is not threading.main_thread()
        started.set()
        assert release.wait(timeout=2)
        return "derived"

    monkeypatch.setattr(auth, "_hash_password", derive)
    task = asyncio.create_task(auth.set_parameters_async("a" * 32, 100000))
    try:

        async def thread_started():
            while not started.is_set():
                await asyncio.sleep(0)

        await asyncio.wait_for(thread_started(), 1)
        assert not task.done()  # The loop is responsive while the worker is blocked.
    finally:
        release.set()
        await task
    assert auth.password_hash == "derived"


@pytest.mark.asyncio
async def test_cancelled_derivation_cannot_mutate_authenticator(monkeypatch):
    auth = Authenticator("test-password")
    original = (auth.salt, auth.iterations, auth.password_hash)
    started = asyncio.Event()

    async def worker(*_args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(asyncio, "to_thread", worker)
    task = asyncio.create_task(auth.set_parameters_async("b" * 32, 100000))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (auth.salt, auth.iterations, auth.password_hash) == original


@pytest.mark.asyncio
async def test_network_challenge_rejected_before_kdf_dispatch(monkeypatch):
    client = VirtualGamepadClient(
        "localhost", 9999, "tcp", Mock(), password="test-password"
    )
    handler = Mock()
    handler.read_message = AsyncMock(
        return_value={
            "type": "auth_challenge",
            "protocol_version": "2.0",
            "challenge": "c" * 32,
            "salt": "a" * 32,
            "iterations": 2_000_000_000,
        }
    )
    dispatch = AsyncMock()
    monkeypatch.setattr(asyncio, "to_thread", dispatch)
    assert not await client._tcp_auth(handler)
    dispatch.assert_not_awaited()


def test_port_rotation_cannot_bypass_ip_limit(monkeypatch):
    monkeypatch.setattr("padrelay.security.rate_limiting.time.monotonic", lambda: 1000)
    tracker = ConnectionTracker(max_requests=1)
    assert not tracker.is_rate_limited(("127.0.0.1", 1))
    for port in range(2, 1002):
        assert tracker.is_rate_limited(("127.0.0.1", port))
    assert len(tracker.clients) == 1


def test_tracking_saturation_cannot_evict_blocks(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(
        "padrelay.security.rate_limiting.time.monotonic", lambda: now[0]
    )
    tracker = ConnectionTracker(
        max_requests=1, max_tracked_ips=2, global_max_requests=10000
    )
    assert not tracker.is_rate_limited(("192.0.2.1", 1))
    assert tracker.is_rate_limited(("192.0.2.1", 2))
    assert not tracker.is_rate_limited(("192.0.2.2", 1))
    for i in range(3, 1000):
        assert tracker.is_rate_limited((f"198.51.100.{i}", 1))
    assert len(tracker.clients) == 2
    assert tracker.is_blocked(("192.0.2.1", 9999))
    now[0] += 61
    assert not tracker.is_rate_limited(("192.0.2.3", 1))
    assert len(tracker.clients) == 1


def test_global_budget_rejects_before_allocating_per_ip_state(monkeypatch):
    monkeypatch.setattr("padrelay.security.rate_limiting.time.monotonic", lambda: 1000)
    tracker = ConnectionTracker(global_max_requests=2)
    assert not tracker.is_rate_limited(("192.0.2.1", 1))
    assert not tracker.is_rate_limited(("192.0.2.2", 1))
    assert tracker.is_rate_limited(("192.0.2.3", 1))
    assert len(tracker.clients) == 2


def test_live_connection_not_expired_by_limiter_cleanup(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(
        "padrelay.security.rate_limiting.time.monotonic", lambda: now[0]
    )
    tracker = ConnectionTracker()
    assert tracker.reserve(("127.0.0.1", 1))
    tracker.authenticate(("127.0.0.1", 1))
    now[0] += 10000
    tracker.is_rate_limited(("127.0.0.2", 1))
    assert not tracker.reserve(("127.0.0.2", 1))
    tracker.disconnect(("127.0.0.1", 1))
    assert tracker.reserve(("127.0.0.2", 1))


@pytest.mark.asyncio
async def test_pending_connection_reserved_before_challenge_and_released(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    async with running_server(password="test-password") as server:
        r1, w1 = await asyncio.open_connection(*address(server))
        first = TCPProtocolHandler(r1, w1)
        challenge = await first.read_message()
        assert challenge["type"] == "auth_challenge"
        assert server.tracker.pending_connections == 1
        r2, w2 = await asyncio.open_connection(*address(server))
        second = TCPProtocolHandler(r2, w2)
        try:
            result = await asyncio.wait_for(second.read_message(), 1)
            assert result["type"] == "error"
            auth = Authenticator("test-password")
            auth.set_parameters(challenge["salt"], challenge["iterations"])
            await first.send_message(
                {
                    "type": "auth_response",
                    "protocol_version": "2.0",
                    "response": auth.generate_tcp_response(challenge["challenge"]),
                }
            )
            await first.drain()
            assert (await first.read_message())["type"] == "auth_success"
            assert server.tracker.active_connections == 1
            assert server.tracker.pending_connections == 0
        finally:
            first.close()
            second.close()
            await first.wait_closed()
            await second.wait_closed()
    assert server.tracker.active_connections == server.tracker.pending_connections == 0


@pytest.mark.asyncio
async def test_pending_auth_cancellation_and_shutdown_release_slots(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    async with running_server(password="test-password") as server:
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        assert (await handler.read_message())["type"] == "auth_challenge"
        assert server.tracker.pending_connections == 1
        for task in list(server.client_tasks):
            task.cancel()
        await asyncio.gather(*list(server.client_tasks), return_exceptions=True)
        assert server.tracker.pending_connections == 0
        handler.close()
        await handler.wait_closed()
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        assert (await handler.read_message())["type"] == "auth_challenge"
        await asyncio.wait_for(server.shutdown(), 1)
        assert server.tracker.pending_connections == 0
        handler.close()
        await handler.wait_closed()


@pytest.mark.asyncio
async def test_udp_session_revoked_when_tls_control_disconnects(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    async with running_server(protocol="udp", password="test-password") as server:
        client = VirtualGamepadClient(
            *address(server),
            "udp",
            Mock(),
            password="test-password",
            ca_path=tls_utils.DEFAULT_CERT_FILE,
        )
        reader, writer = await asyncio.open_connection(
            *address(server), ssl=client.ssl_context, server_hostname="localhost"
        )
        handler = TCPProtocolHandler(reader, writer)
        assert await client._tcp_auth(handler)
        session = client.udp_session
        assert session.session_id in server.udp_sessions
        from padrelay.core.controller_state import InputState

        packet = session.encode(InputState(frozenset({"a"})).to_message())
        handler.close()
        await handler.wait_closed()
        await asyncio.wait_for(asyncio.gather(*list(server.client_tasks)), 1)
        assert not server.udp_sessions
        recording = Mock()
        protocol = UDPServerProtocol(recording, server.udp_sessions)
        protocol.connection_made(Mock())
        protocol.datagram_received(packet, ("127.0.0.1", 9999))
        recording.process.assert_not_called()


@pytest.mark.parametrize(
    "parser, command",
    [
        (config.parse_client_args, "padrelay-client"),
        (config.parse_server_args, "padrelay-server"),
    ],
)
def test_udp_cannot_disable_control_tls(monkeypatch, parser, command):
    monkeypatch.setattr(
        "sys.argv",
        [command, "--protocol", "udp", "--disable-tls", "--password", "test-password"],
    )
    with pytest.raises(ValueError, match="TLS control"):
        parser()


@pytest.mark.asyncio
async def test_tcp_failed_attempt_budget_is_shared_across_ports(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    async with running_server(password="test-password") as server:
        server.auth_tracker = ConnectionTracker(max_requests=1)
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        assert (await handler.read_message())["type"] == "auth_challenge"
        await handler.send_message(
            {
                "type": "auth_response",
                "protocol_version": "2.0",
                "response": "incorrect",
            }
        )
        await handler.drain()
        assert (await handler.read_message())["type"] == "auth_failed"
        handler.close()
        await handler.wait_closed()
        await asyncio.gather(*list(server.client_tasks))
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        try:
            assert (await handler.read_message())["type"] == "error"
            assert (
                server.tracker.pending_connections
                == server.tracker.active_connections
                == 0
            )
        finally:
            handler.close()
            await handler.wait_closed()


@pytest.mark.asyncio
async def test_authentication_timeout_releases_reservation(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)
    async with running_server(password="test-password") as server:

        async def timeout(_handler):
            raise TimeoutError("authentication deadline")

        monkeypatch.setattr(server, "_authenticate_client", timeout)
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        assert await asyncio.wait_for(handler.read_message(), 1) is None
        await asyncio.gather(*list(server.client_tasks))
        assert server.tracker.pending_connections == 0
        handler.close()
        await handler.wait_closed()
