"""Real loopback sockets and application loops; only gamepad hardware is replaced."""

import asyncio
import copy
import ssl
from contextlib import asynccontextmanager

import pytest

from padrelay.client import client_app
from padrelay.protocol.constants import PROTOCOL_VERSION
from padrelay.protocol.tcp import TCPProtocolHandler
from padrelay.security import tls_utils
from padrelay.security.auth import Authenticator
from padrelay.server import server_app

PASSWORD = "integration-test-password"
FRAMES = [
    {
        "buttons": [True, False],
        "axes": [0.25, -0.5, 0.75, -1.0],
        "triggers": [0.4, 0.8],
    },
    {
        "buttons": [False, True],
        "axes": [-0.75, 0.5, -0.25, 1.0],
        "triggers": [0.9, 0.3],
    },
]


class RecordingGamepad:
    def __init__(self, *args, **kwargs):
        self.buttons = set()
        self.state = {}
        self.frames = []
        self.updated = asyncio.Event()
        self.resets = 0

    def get_button_mapping(self):
        return {0: 1, 1: 2}

    def press_button(self, button):
        self.buttons.add(button)

    def release_button(self, button):
        self.buttons.discard(button)

    def left_joystick_float(self, x_value_float, y_value_float):
        self.state["left"] = (x_value_float, y_value_float)

    def right_joystick_float(self, x_value_float, y_value_float):
        self.state["right"] = (x_value_float, y_value_float)

    def left_trigger_float(self, value_float):
        self.state["left_trigger"] = value_float

    def right_trigger_float(self, value_float):
        self.state["right_trigger"] = value_float

    def update(self):
        self.frames.append(dict(self.state, buttons=set(self.buttons)))
        self.updated.set()

    def reset_gamepad_state(self):
        self.resets += 1


class ScriptedInput:
    def __init__(self):
        self.frames = iter(FRAMES)
        self.cleaned = False
        self.polled = 0

    def poll(self):
        self.polled += 1
        frame = next(self.frames, None)
        if frame is None:
            return None
        return dict(
            copy.deepcopy(frame),
            type="input",
            protocol_version=PROTOCOL_VERSION,
            hats=[],
        )

    def cleanup(self):
        self.cleaned = True


@pytest.fixture
def network_hardware(monkeypatch):
    monkeypatch.setattr(server_app, "VirtualGamepad", RecordingGamepad)


@asynccontextmanager
async def running_server(protocol="tcp", password=PASSWORD, **options):
    server = server_app.VirtualGamepadServer(
        "127.0.0.1", 0, password=password, protocol=protocol, **options
    )
    task = asyncio.create_task(server.run())

    async def ready():
        while not server.server:
            if task.done():
                pytest.fail(f"Server exited before listening: {task.result()}")
            await asyncio.sleep(0.005)

    try:
        await asyncio.wait_for(ready(), timeout=3)
        yield server
    finally:
        await asyncio.wait_for(server.shutdown(), timeout=3)
        task.cancel()
        await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=3)


def address(server):
    if server.protocol == "tcp":
        return server.server.sockets[0].getsockname()
    return server.transport.get_extra_info("sockname")


async def transfer(server, monkeypatch, password=PASSWORD, **options):
    """Verify gamepad states and heartbeat acknowledgments over real sockets."""
    heartbeat_ack = asyncio.Event()
    original_read = TCPProtocolHandler.read_message

    async def read_message(handler):
        message = await original_read(handler)
        if message and message.get("type") == "heartbeat_ack":
            heartbeat_ack.set()
        return message

    monkeypatch.setattr(TCPProtocolHandler, "read_message", read_message)
    monkeypatch.setattr(client_app, "HEARTBEAT_INTERVAL", 0.05)
    if server.protocol == "udp":
        options.setdefault("ca_path", tls_utils.DEFAULT_CERT_FILE)
    gamepad = ScriptedInput()
    client = client_app.VirtualGamepadClient(
        *address(server),
        server.protocol,
        gamepad,
        password=password,
        update_rate=30,
        **options,
    )
    if client.ssl_context:
        # Verify test certificates with OpenSSL strict X.509 validation enabled.
        client.ssl_context.verify_flags |= ssl.VERIFY_X509_STRICT
    task = asyncio.create_task(client.run())

    async def frames_received():
        while len(server.virtual_gamepad.frames) < len(FRAMES):
            await server.virtual_gamepad.updated.wait()
            server.virtual_gamepad.updated.clear()

    try:
        await asyncio.wait_for(frames_received(), timeout=3)
        await asyncio.wait_for(heartbeat_ack.wait(), timeout=3)
        assert client.connected
        assert server.virtual_gamepad.frames == [
            {
                "buttons": {1},
                "left": (0.25, -0.5),
                "right": (0.75, -1.0),
                "left_trigger": 0.4,
                "right_trigger": 0.8,
            },
            {
                "buttons": {2},
                "left": (-0.75, 0.5),
                "right": (-0.25, 1.0),
                "left_trigger": 0.9,
                "right_trigger": 0.3,
            },
        ]
        if server.enable_tls:
            assert server.active_clients
            for writer in server.active_clients:
                connection = writer.get_extra_info("ssl_object")
                assert connection.version() in {"TLSv1.2", "TLSv1.3"}
                assert connection.cipher()[2] >= 128
        elif server.protocol == "tcp":
            assert all(
                writer.get_extra_info("ssl_object") is None
                for writer in server.active_clients
            )
    finally:
        await asyncio.wait_for(client.shutdown(), timeout=3)
        task.cancel()
        await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=3)
    assert gamepad.cleaned


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
@pytest.mark.parametrize("credentials", ["plain", "hashed-server", "hashed-both"])
async def test_authenticated_data_exchange(
    network_hardware, monkeypatch, protocol, credentials
):
    hashed = Authenticator.hash_password(PASSWORD)
    server_password = PASSWORD if credentials == "plain" else hashed
    client_password = hashed if credentials == "hashed-both" else PASSWORD
    async with running_server(protocol, password=server_password) as server:
        await transfer(server, monkeypatch, password=client_password)


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_reconnect_applies_unchanged_input_immediately(
    network_hardware, protocol
):
    async with running_server(protocol) as server:
        client = client_app.VirtualGamepadClient(
            *address(server),
            protocol,
            ScriptedInput(),
            password=PASSWORD,
            ca_path=tls_utils.DEFAULT_CERT_FILE,
        )
        message = dict(FRAMES[0], type="input", protocol_version=PROTOCOL_VERSION)
        for connection in range(2):
            reader, writer = await asyncio.open_connection(
                *address(server),
                ssl=client.ssl_context,
                server_hostname="localhost" if client.ssl_context else None,
            )
            handler = TCPProtocolHandler(reader, writer)
            transport = None
            server.virtual_gamepad.updated.clear()
            try:
                assert await client._tcp_auth(handler)
                if protocol == "udp":
                    (
                        transport,
                        _,
                    ) = await asyncio.get_running_loop().create_datagram_endpoint(
                        asyncio.DatagramProtocol, remote_addr=address(server)
                    )
                    transport.sendto(client.udp_session.encode(message))
                else:
                    assert await handler.send_message(message)
                    assert await handler.drain()
                await asyncio.wait_for(server.virtual_gamepad.updated.wait(), 1)
                assert len(server.virtual_gamepad.frames) == connection + 1
                assert server.virtual_gamepad.frames[-1]["buttons"] == {1}
            finally:
                if transport:
                    transport.close()
                handler.close()
                await handler.wait_closed()
                await asyncio.wait_for(asyncio.gather(*list(server.client_tasks)), 2)


@pytest.mark.asyncio
async def test_tcp_validates_first_input_before_processing(network_hardware):
    async with running_server(password=None) as server:
        reader, writer = await asyncio.open_connection(*address(server))
        handler = TCPProtocolHandler(reader, writer)
        try:
            await handler.send_message(
                {"type": "input", "buttons": [True], "axes": [99]}
            )
            await handler.send_message({"type": "heartbeat"})
            await handler.drain()
            assert (await asyncio.wait_for(handler.read_message(), 1))[
                "type"
            ] == "heartbeat_ack"
            assert server.virtual_gamepad.frames == []
        finally:
            handler.close()
            await handler.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize("certificate", ["supplied", "autogenerated", "private-ca"])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_tls_data_exchange(
    network_hardware, monkeypatch, tmp_path, issued_certificate, certificate, protocol
):
    options = {}
    if certificate == "private-ca":
        cert, key, trust = issued_certificate(hostname="padrelay.test")
        original = (cert.read_bytes(), key.read_bytes())
        options = {"cert_path": cert, "key_path": key}
    elif certificate == "supplied":
        cert, key = tls_utils.generate_self_signed_cert(
            tmp_path / "provided.crt",
            tmp_path / "provided.key",
            common_name="padrelay.test",
        )
        trust = cert
        original = (cert.read_bytes(), key.read_bytes())
        options = {"cert_path": cert, "key_path": key}
    else:
        cert, key = tls_utils.get_default_cert_paths()
        trust = cert
        assert not cert.exists() and not key.exists()

    async with running_server(protocol=protocol, enable_tls=True, **options) as server:
        assert cert.exists() and key.exists()
        await transfer(
            server,
            monkeypatch,
            enable_tls=True,
            ca_path=trust,
            server_hostname=(
                "padrelay.test" if certificate != "autogenerated" else "localhost"
            ),
        )

    if certificate != "autogenerated":
        assert (cert.read_bytes(), key.read_bytes()) == original
    else:
        # The identity must survive a restart so the copied trust certificate stays valid.
        original = (cert.read_bytes(), key.read_bytes())
        async with running_server(protocol=protocol, enable_tls=True) as server:
            await transfer(server, monkeypatch, enable_tls=True, ca_path=cert)
        assert (cert.read_bytes(), key.read_bytes()) == original


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["untrusted", "wrong-hostname", "expired"])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_tls_rejects_invalid_server(
    network_hardware, monkeypatch, issued_certificate, reason, protocol
):
    cert, key, trust = issued_certificate(expired=reason == "expired")
    async with running_server(
        protocol=protocol, enable_tls=True, cert_path=cert, key_path=key
    ) as server:
        gamepad = ScriptedInput()
        client = client_app.VirtualGamepadClient(
            *address(server),
            protocol,
            gamepad,
            password=PASSWORD,
            enable_tls=True,
            ca_path=None if reason == "untrusted" else trust,
            server_hostname=(
                "unrelated.invalid" if reason == "wrong-hostname" else "localhost"
            ),
        )
        errors = []
        original_connect = asyncio.open_connection

        async def connect(*args, **kwargs):
            assert kwargs["ssl"] is client.ssl_context
            try:
                return await original_connect(*args, **kwargs)
            except ssl.SSLCertVerificationError as error:
                errors.append(error)
                client.shutdown_event.set()
                raise

        monkeypatch.setattr(client_app.asyncio, "open_connection", connect)
        try:
            await asyncio.wait_for(client.run(), timeout=3)
        finally:
            await client.shutdown()
        assert len(errors) == 1
        assert (
            errors[0].verify_code
            == {"untrusted": 20, "wrong-hostname": 62, "expired": 10}[reason]
        )
        assert not client.connected
        assert gamepad.polled == 0
        assert not server.virtual_gamepad.frames


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["tcp", "udp", "tls"])
async def test_wrong_password_does_not_deliver_input(
    network_hardware, monkeypatch, mode
):
    rejected = asyncio.Event()
    protocol = "udp" if mode == "udp" else "tcp"
    method = "verify_tcp_response"
    original = getattr(Authenticator, method)

    def verify(authenticator, *args, **kwargs):
        accepted = original(authenticator, *args, **kwargs)
        if not accepted:
            rejected.set()
        return accepted

    monkeypatch.setattr(Authenticator, method, verify)
    async with running_server(protocol, enable_tls=mode == "tls") as server:
        gamepad = ScriptedInput()
        client = client_app.VirtualGamepadClient(
            *address(server),
            protocol,
            gamepad,
            password="wrong-password",
            enable_tls=mode == "tls",
            ca_path=tls_utils.DEFAULT_CERT_FILE if mode != "tcp" else None,
        )
        task = asyncio.create_task(client.run())
        try:
            await asyncio.wait_for(rejected.wait(), timeout=3)
            assert not server.virtual_gamepad.frames
        finally:
            await client.shutdown()
            task.cancel()
            await asyncio.wait_for(
                asyncio.gather(task, return_exceptions=True), timeout=3
            )
