"""Client application"""

import asyncio
import socket
import ssl
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.exceptions import ConnectionError as RelayConnectionError
from ..core.logging_utils import get_logger
from ..protocol.constants import HEARTBEAT_INTERVAL, PROTOCOL_VERSION
from ..protocol.tcp import TCPProtocolHandler
from ..protocol.udp import UDPProtocolHandler
from ..security.auth import Authenticator
from ..security.tls_utils import create_client_ssl_context
from ..security.udp_session import UDPSession
from .constants import RECONNECT_DELAY
from .input import GamepadInput

logger = get_logger(__name__)


class VirtualGamepadClient:
    """Client controller"""

    def __init__(
        self,
        server_ip: str,
        server_port: int,
        protocol: str,
        gamepad: GamepadInput,
        update_rate: int = 60,
        password: Optional[str] = None,
        config: Optional[object] = None,
        enable_tls: bool = False,
        ca_path: Optional[Path] = None,
        server_hostname: Optional[str] = None,
    ) -> None:
        """Construct the client and configure networking"""
        self.server_ip = server_ip
        self.server_port = server_port
        self.protocol = protocol.lower()
        self.gamepad = gamepad
        self.update_rate = update_rate
        self.config = config
        self.enable_tls = enable_tls or self.protocol == "udp"
        if self.protocol == "udp" and not password:
            raise ValueError("Secure UDP requires a password")
        self.udp_session: Optional[UDPSession] = None
        self.ssl_context: Optional[ssl.SSLContext] = None
        self.server_hostname = server_hostname or server_ip

        # Security
        self.authenticator = Authenticator(password)

        # Initialize TLS if enabled
        if self.enable_tls:
            self.ssl_context = create_client_ssl_context(ca_path=ca_path)
            logger.info(
                "TLS/SSL encryption and server certificate verification enabled"
            )
        else:
            if self.protocol == "tcp":
                logger.warning(
                    "TLS/SSL encryption is DISABLED. "
                    "Network traffic will be transmitted in plaintext. "
                    "Use --enable-tls to enable encryption, or ensure you're on a trusted network."
                )

        # Connection state
        self.connected = False
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Tasks
        self.main_task: Optional[asyncio.Task[bool]] = None
        self.heartbeat_task: Optional[asyncio.Task[bool]] = None

        logger.info(f"Client initialized with {self.protocol.upper()} protocol")
        logger.info(f"Server: {self.server_ip}:{self.server_port}")
        logger.info(f"Update rate: {self.update_rate} Hz")

    async def run(self) -> bool:
        """Run the client using the chosen protocol"""
        self.running = True
        self.main_task = asyncio.current_task()

        try:
            if self.protocol == "tcp":
                await self._run_tcp()
            else:
                await self._run_udp()
            return True
        except asyncio.CancelledError:
            logger.info("Client cancelled")
            return self.shutdown_event.is_set()
        except Exception as e:
            logger.error(f"Client error: {e}")
            return False
        finally:
            self.running = False
            self.main_task = None

    async def shutdown(self) -> bool:
        """Shut down tasks and clean up resources"""
        logger.info("Shutdown initiated...")
        self.shutdown_event.set()

        # Cancel heartbeat task
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Cancel main task
        if (
            self.main_task
            and self.main_task is not asyncio.current_task()
            and not self.main_task.done()
        ):
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass

        # Cleanup gamepad
        self.gamepad.cleanup()

        logger.info("Shutdown complete")
        return True

    async def _wait_for_controller(self) -> bool:
        while not self.shutdown_event.is_set():
            if self.gamepad.is_available():
                return True
            try:
                await asyncio.wait_for(self.shutdown_event.wait(), 0.1)
            except asyncio.TimeoutError:
                pass
        return False

    async def _run_tcp(self) -> None:
        """Main loop for TCP mode"""
        while not self.shutdown_event.is_set():
            if not await self._wait_for_controller():
                break
            tcp_handler = None
            try:
                # Connect to server
                logger.info(
                    f"Connecting to TCP server at {self.server_ip}:{self.server_port}..."
                )
                reader, writer = await asyncio.open_connection(
                    self.server_ip,
                    self.server_port,
                    ssl=self.ssl_context if self.enable_tls else None,
                    server_hostname=self.server_hostname if self.enable_tls else None,
                )

                logger.info(
                    f"Connected to server at {self.server_ip}:{self.server_port}"
                )

                # Log TLS connection details if enabled
                if self.enable_tls:
                    ssl_object = writer.get_extra_info("ssl_object")
                    if ssl_object:
                        cipher = ssl_object.cipher()
                        tls_version = ssl_object.version()
                        logger.info("TLS handshake successful")
                        logger.debug("TLS connection details:")
                        logger.debug(f"  TLS version: {tls_version}")
                        if cipher:
                            logger.debug(f"  Cipher: {cipher[0]} (bits: {cipher[2]})")
                            logger.debug(f"  Protocol: {cipher[1]}")
                    else:
                        logger.warning("TLS enabled but no SSL object found")

                # Initialize protocol handler
                tcp_handler = TCPProtocolHandler(reader, writer)

                # Optimize socket settings
                sock = writer.get_extra_info("socket")
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

                # Authenticate
                if not await self._tcp_auth(tcp_handler):
                    raise RelayConnectionError("Authentication rejected")

                # Start heartbeat task
                self.heartbeat_task = asyncio.create_task(
                    self._tcp_heartbeat_loop(tcp_handler)
                )

                # Set connection state
                self.connected = True

                # Main sending loop
                send_interval = 1.0 / self.update_rate
                last_send_time = time.time()

                while not self.shutdown_event.is_set():
                    # Poll gamepad and send update
                    message = self.gamepad.poll()
                    if message is None:
                        logger.warning(
                            "Controller unavailable; closing session to reset output"
                        )
                        break
                    if message:
                        if not await tcp_handler.send_message(message):
                            break
                        if not await tcp_handler.drain():
                            break
                        if writer.is_closing():
                            logger.warning("Server closed the connection")
                            break

                    # Calculate sleep time to maintain consistent update rate
                    current_time = time.time()
                    elapsed = current_time - last_send_time
                    sleep_time = max(0, send_interval - elapsed)

                    # Adaptive timing - if we're behind schedule, catch up gradually
                    if sleep_time < 0:
                        sleep_time = 0
                        # Reset timing if we fall too far behind
                        if elapsed > send_interval * 3:
                            logger.warning("Timing drift detected, resetting schedule")
                            last_send_time = current_time
                    else:
                        last_send_time = current_time + sleep_time

                    await asyncio.sleep(sleep_time)

                    # Check if heartbeat task failed
                    if self.heartbeat_task.done():
                        if self.heartbeat_task.exception():
                            logger.error(
                                f"Heartbeat task failed: {self.heartbeat_task.exception()}"
                            )
                        else:
                            logger.warning("Heartbeat task ended")
                        break

            except asyncio.CancelledError:
                logger.info("TCP send loop cancelled")
                break
            except Exception as e:
                logger.error(f"TCP connection error: {e}")

            finally:
                self.connected = False
                try:
                    if tcp_handler is not None:
                        tcp_handler.close()
                        await tcp_handler.wait_closed()
                    if self.heartbeat_task and not self.heartbeat_task.done():
                        self.heartbeat_task.cancel()
                        try:
                            await self.heartbeat_task
                        except asyncio.CancelledError:
                            pass
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")

            # Reconnect after delay
            if not self.shutdown_event.is_set():
                logger.info(f"Reconnecting in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def _tcp_auth(self, tcp_handler) -> bool:
        """Authenticate with the server over TCP"""
        try:
            # Wait for auth challenge from server
            logger.debug("Waiting for authentication challenge from server")
            challenge_msg = await asyncio.wait_for(tcp_handler.read_message(), 5)
            if not challenge_msg or challenge_msg.get("type") != "auth_challenge":
                logger.error("Authentication protocol error: Invalid challenge")
                return False

            logger.debug("Received authentication challenge")

            # Extract challenge and verify protocol version
            challenge = challenge_msg.get("challenge")
            salt = challenge_msg.get("salt")
            iterations = challenge_msg.get("iterations")
            if challenge_msg.get("protocol_version") != PROTOCOL_VERSION:
                return False
            if (
                not isinstance(challenge, str)
                or len(challenge) != 32
                or not challenge.isascii()
            ):
                return False
            await self.authenticator.set_parameters_async(salt, iterations)

            # Calculate HMAC response
            logger.debug("Generating authentication response")
            response = self.authenticator.generate_tcp_response(challenge)

            # Send auth response
            logger.debug("Sending authentication response")
            auth_response = {
                "type": "auth_response",
                "protocol_version": PROTOCOL_VERSION,
                "response": response,
            }
            await tcp_handler.send_message(auth_response)
            await tcp_handler.drain()

            # Wait for auth result
            logger.debug("Waiting for authentication result")
            result = await asyncio.wait_for(tcp_handler.read_message(), 5)
            if not result:
                return False

            if (
                result.get("type") == "auth_success"
                and result.get("protocol_version") == PROTOCOL_VERSION
            ):
                if self.protocol == "udp":
                    if not self.ssl_context or not self.ssl_context.check_hostname:
                        return False
                    self.udp_session = UDPSession.from_parameters(result["udp_session"])
                logger.info("Authentication successful")
                return True
            else:
                logger.error(
                    f"Authentication failed: {result.get('message', 'Unknown error')}"
                )
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def _tcp_heartbeat_loop(
        self, tcp_handler, interval: int = HEARTBEAT_INTERVAL
    ) -> bool:
        """Send heartbeats at ``interval`` seconds"""
        while not self.shutdown_event.is_set():
            try:
                heartbeat = {
                    "type": "heartbeat",
                    "protocol_version": PROTOCOL_VERSION,
                    "timestamp": datetime.now().isoformat(),
                }
                await tcp_handler.send_message(heartbeat)
                await tcp_handler.drain()

                # Wait for heartbeat acknowledgment with timeout
                try:
                    response = await asyncio.wait_for(
                        tcp_handler.read_message(), timeout=5.0
                    )
                    if not response or response.get("type") != "heartbeat_ack":
                        logger.warning("Invalid heartbeat response")
                        return False
                except asyncio.TimeoutError:
                    logger.warning("Heartbeat acknowledgment timeout")
                    return False

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                return True
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                return False
        return True

    async def _run_udp(self) -> None:
        """TLS owns authentication, key distribution, heartbeat and UDP lifetime."""
        loop = asyncio.get_running_loop()
        while not self.shutdown_event.is_set():
            if not await self._wait_for_controller():
                break
            tcp_handler = None
            udp_handler = None
            self.udp_session = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        self.server_ip,
                        self.server_port,
                        ssl=self.ssl_context,
                        server_hostname=self.server_hostname,
                    ),
                    10,
                )
                tcp_handler = TCPProtocolHandler(reader, writer)
                if not await self._tcp_auth(tcp_handler) or self.udp_session is None:
                    raise RelayConnectionError("Secure UDP authentication failed")
                session = self.udp_session
                transport, _ = await loop.create_datagram_endpoint(
                    asyncio.DatagramProtocol,
                    remote_addr=(self.server_ip, self.server_port),
                )
                udp_handler = UDPProtocolHandler(transport)
                self.heartbeat_task = asyncio.create_task(
                    self._tcp_heartbeat_loop(tcp_handler, interval=HEARTBEAT_INTERVAL)
                )
                self.connected = True
                while not self.shutdown_event.is_set():
                    if (
                        self.heartbeat_task.done()
                        or time.monotonic() >= session.expires_at
                    ):
                        break
                    message = self.gamepad.poll()
                    if message is None:
                        logger.warning(
                            "Controller unavailable; closing session to reset output"
                        )
                        break
                    if message and not udp_handler.send_message(
                        session.encode(message)
                    ):
                        break
                    await asyncio.sleep(1.0 / self.update_rate)
            except asyncio.CancelledError:
                break
            except (
                asyncio.TimeoutError,
                OSError,
                ValueError,
                RelayConnectionError,
            ) as exc:
                logger.warning(f"Secure UDP connection closed: {exc}")
            finally:
                self.connected = False
                self.udp_session = None
                if udp_handler is not None:
                    udp_handler.close()
                if self.heartbeat_task and not self.heartbeat_task.done():
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                if tcp_handler is not None:
                    tcp_handler.close()
                    await tcp_handler.wait_closed()
            if not self.shutdown_event.is_set():
                await asyncio.sleep(RECONNECT_DELAY)
