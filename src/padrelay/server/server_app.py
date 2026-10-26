"""Server application for the PadRelay"""

import asyncio
import socket
import ssl
import time
from pathlib import Path
from typing import Optional

from ..core.logging_utils import get_logger
from ..protocol.constants import HEARTBEAT_INTERVAL
from ..protocol.messages import validate_input_message
from ..protocol.tcp import TCPProtocolHandler
from ..protocol.udp import UDPServerProtocol
from ..security.auth import Authenticator
from ..security.rate_limiting import ConnectionTracker
from ..security.tls_utils import create_server_ssl_context, warn_if_cert_expiring_soon
from ..security.udp_session import UDPSession
from .constants import (
    DEFAULT_BLOCK_DURATION,
    MAX_CONNECTIONS,
)
from .input_processor import GamepadHandler
from .virtual_gamepad import VirtualGamepad

logger = get_logger(__name__)


class VirtualGamepadServer:
    """Server controller"""

    def __init__(
        self,
        host,
        port,
        password,
        gamepad_type="xbox360",
        config=None,
        rate_limit_window=60,
        max_requests=100,
        block_duration=DEFAULT_BLOCK_DURATION,
        protocol="tcp",
        enable_tls=False,
        cert_path: Optional[Path] = None,
        key_path: Optional[Path] = None,
    ):
        """Construct the server instance

        Args:
            host: Host to bind to
            port: Port to listen on
            password: Authentication password
            gamepad_type: Type of virtual gamepad to create
            config: Configuration object (optional)
            rate_limit_window: Time window for rate limiting in seconds
            max_requests: Maximum number of requests per window
            block_duration: How long to block clients that exceed the rate limit
            protocol: Transport protocol ('tcp' or 'udp')
            enable_tls: Enable TLS for TCP data; UDP control always requires TLS
            cert_path: Path to TLS certificate (optional)
            key_path: Path to TLS private key (optional)
        """
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.config = config
        self.password = password
        self.enable_tls = enable_tls or self.protocol == "udp"
        if self.protocol == "udp" and not password:
            raise ValueError("Secure UDP requires a password")
        self.cert_path = cert_path
        self.key_path = key_path
        self.ssl_context: Optional[ssl.SSLContext] = None

        # Initialize active clients tracking
        self.active_clients: set[asyncio.StreamWriter] = set()
        self.server: Optional[asyncio.AbstractServer] = None
        self.transport: Optional[asyncio.DatagramTransport] = None

        # Security
        self.authenticator = Authenticator(password)
        self.tracker = ConnectionTracker(
            max_connections=MAX_CONNECTIONS,
            rate_limit_window=rate_limit_window,
            max_requests=max_requests,
            block_duration=block_duration,
        )

        self.auth_tracker = ConnectionTracker(
            max_requests=min(max_requests, 10), global_max_requests=1000
        )
        self.udp_sessions: dict[bytes, UDPSession] = {}
        self.client_tasks: set[asyncio.Task] = set()

        # Fail TLS setup before allocating gamepad resources.
        if self.enable_tls:
            if (cert_path is None) != (key_path is None):
                raise ValueError(
                    "TLS certificate and private key must be supplied together"
                )
            self.ssl_context = create_server_ssl_context(
                cert_path,
                key_path,
                auto_generate=cert_path is None and key_path is None,
            )
            warn_if_cert_expiring_soon(cert_path)

        # Virtual gamepad
        self.gamepad_type = gamepad_type
        self.virtual_gamepad = VirtualGamepad(gamepad_type, config)

        # Input processor
        self.gamepad_handler = GamepadHandler(self.virtual_gamepad, config)

        # Shutdown handling
        self.shutdown_event = asyncio.Event()

        logger.info(f"Server initialized with {self.protocol.upper()} protocol")
        logger.info(f"Listening on: {self.host}:{self.port}")
        logger.info(f"Gamepad type: {self.gamepad_type}")

        # Report transport security.
        if self.enable_tls:
            logger.info("TLS/SSL encryption enabled")
        else:
            if self.protocol == "tcp":
                logger.warning(
                    "TLS/SSL encryption is DISABLED. "
                    "Network traffic will be transmitted in plaintext. "
                    "Use --enable-tls to enable encryption, or ensure you're on a trusted network."
                )

        if not self.password:
            logger.warning(
                "Server is running without authentication! "
                "This means anyone on the network can connect. "
                "To secure access, set a password using the '--password' flag, "
                "a config file entry, or environment variable (PASSWORD or PASSWORD_HASH)."
            )

    async def run(self):
        """Run the server with the configured protocol"""
        try:
            if self.protocol == "udp":
                await self._run_udp_server()
            else:
                await self._run_tcp_server()
            return True
        except Exception as e:
            logger.error(f"Server error: {e}")
            return False

    async def shutdown(self):
        """Close all connections and shut down"""
        logger.info("Shutdown initiated...")
        self.shutdown_event.set()

        # Close all active client connections
        close_tasks = []
        for writer in self.active_clients:
            try:
                writer.close()
                close_tasks.append(writer.wait_closed())
            except Exception as e:  # pragma: no cover - safety net
                logger.error(f"Error closing connection: {e}")

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if self.client_tasks:
            await asyncio.gather(*list(self.client_tasks), return_exceptions=True)
        if self.transport:
            self.transport.close()

        # Reset gamepad state
        self.gamepad_handler.reset()

        logger.info("All connections closed")
        return True

    async def _run_tcp_server(self) -> None:
        """Start the TCP data listener or the UDP session control listener."""
        try:
            server = await asyncio.start_server(
                self._handle_tcp_client,
                self.host,
                self.port,
                ssl=self.ssl_context if self.enable_tls else None,
                ssl_handshake_timeout=5.0 if self.enable_tls else None,
            )

            addr = server.sockets[0].getsockname()
            logger.info(f"TCP server listening on {addr}")

            # Store server reference for clean shutdown
            self.server = server

            # Start task to monitor shutdown event
            shutdown_task = asyncio.create_task(self._monitor_shutdown())

            async with server:
                try:
                    await server.serve_forever()
                except asyncio.CancelledError:
                    logger.info("Server task cancelled")
                finally:
                    if not shutdown_task.done():
                        shutdown_task.cancel()

        except OSError as e:
            logger.error(f"Failed to start TCP server: {e}")
            # Check if the port is already in use
            if (
                e.errno == 98 or e.errno == 10048
            ):  # Address already in use (Linux/Windows)
                logger.error(
                    f"Port {self.port} is already in use. Choose a different port or stop the other server."
                )
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting TCP server: {e}")
            raise

    async def _handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Reserve a slot for pending authentication and release it on every exit."""
        addr = writer.get_extra_info("peername")
        handler = TCPProtocolHandler(reader, writer)
        task = asyncio.current_task()
        admitted = False
        authenticated = False
        session = None
        if task is not None:
            self.client_tasks.add(task)
        try:
            if (
                self.shutdown_event.is_set()
                or self.auth_tracker.is_rate_limited(addr)
                or not self.tracker.reserve(addr)
            ):
                await handler.send_message(
                    {
                        "type": "error",
                        "protocol_version": "1.0",
                        "message": "Another client is already connected or admission is limited.",
                    }
                )
                return
            admitted = True
            self.active_clients.add(
                writer
            )  # Includes pending authentication for shutdown.
            sock = writer.get_extra_info("socket")
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if not await asyncio.wait_for(
                self._authenticate_client(handler), timeout=5
            ):
                return
            self.tracker.authenticate(addr)
            authenticated = True
            result: dict = {"type": "auth_success", "protocol_version": "1.0"}
            if self.protocol == "udp":
                # This listener always uses verified TLS on the client side.
                session = UDPSession.create(addr[0])
                self.udp_sessions[session.session_id] = session
                result["udp_session"] = session.parameters()
            if self.password:
                await handler.send_message(result)
                await handler.drain()
            while not self.shutdown_event.is_set():
                message = await asyncio.wait_for(
                    handler.read_message(), timeout=HEARTBEAT_INTERVAL + 5
                )
                if not message:
                    break
                if session is not None and time.monotonic() >= session.expires_at:
                    break
                if message.get("type") == "heartbeat":
                    await handler.send_message(
                        {"type": "heartbeat_ack", "protocol_version": "1.0"}
                    )
                    await handler.drain()
                elif self.protocol == "tcp" and message.get("type") == "input":
                    if validate_input_message(message):
                        self.gamepad_handler.process(message)
        except (asyncio.TimeoutError, ConnectionError, ValueError) as exc:
            logger.debug(f"Client {addr} closed: {exc}")
        finally:
            if session is not None:
                self.udp_sessions.pop(session.session_id, None)
            handler.close()
            try:
                if admitted:
                    await handler.wait_closed()
                else:
                    # Close rejected TLS connections without waiting for peer close_notify.
                    writer.transport.abort()
            finally:
                self.active_clients.discard(writer)
                if admitted:
                    self.tracker.disconnect(addr)
                if authenticated:
                    self.gamepad_handler.reset()
                if task is not None:
                    self.client_tasks.discard(task)

    async def _authenticate_client(self, handler: TCPProtocolHandler) -> bool:
        if not self.password:
            return True
        challenge = self.authenticator.generate_tcp_challenge()
        await handler.send_message(
            {
                "type": "auth_challenge",
                "protocol_version": "1.0",
                "challenge": challenge,
                "salt": self.authenticator.salt,
                "iterations": self.authenticator.iterations,
            }
        )
        await handler.drain()
        response = await handler.read_message()
        valid = (
            isinstance(response, dict)
            and response.get("type") == "auth_response"
            and response.get("protocol_version") == "1.0"
            and self.authenticator.verify_tcp_response(
                challenge, response.get("response", "")
            )
        )
        if not valid:
            await handler.send_message(
                {"type": "auth_failed", "protocol_version": "1.0"}
            )
            await handler.drain()
        return valid

    async def _monitor_shutdown(self) -> None:
        """Wait for shutdown and close resources"""
        await self.shutdown_event.wait()
        logger.info("Shutdown event detected, closing all connections...")

        # Close all active client connections
        close_tasks = []
        for writer in self.active_clients:
            try:
                writer.close()
                close_tasks.append(writer.wait_closed())
            except Exception as e:  # pragma: no cover - safety net
                logger.error(f"Error closing connection: {e}")

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("All connections closed")

    async def _run_udp_server(self) -> None:
        """Start UDP input and TLS control listeners on the same port number."""
        try:
            loop = asyncio.get_running_loop()

            # Create UDP protocol with the gamepad handler
            transport, _ = await loop.create_datagram_endpoint(
                lambda: UDPServerProtocol(
                    self.gamepad_handler, self.udp_sessions, self.tracker
                ),
                local_addr=(self.host, self.port),
            )

            logger.info(f"UDP server listening on {self.host}:{self.port}")

            # Store transport for cleanup
            self.transport = transport

            try:
                self.port = transport.get_extra_info("sockname")[1]
                await self._run_tcp_server()
            finally:
                transport.close()

        except OSError as e:
            logger.error(f"Failed to start UDP server: {e}")
            # Check if the port is already in use
            if (
                e.errno == 98 or e.errno == 10048
            ):  # Address already in use (Linux/Windows)
                logger.error(
                    f"Port {self.port} is already in use. Choose a different port or stop the other server."
                )
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting UDP server: {e}")
            raise
