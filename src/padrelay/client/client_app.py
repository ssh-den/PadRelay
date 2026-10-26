"""Client application"""
import asyncio
import time
import random
import json
import ssl
from datetime import datetime
import socket
from typing import Optional
from ..core.logging_utils import get_logger
from ..core.exceptions import AuthenticationError, ConnectionError
from ..protocol.constants import HEARTBEAT_INTERVAL, PROTOCOL_VERSION
from ..protocol.tcp import TCPProtocolHandler
from ..protocol.udp import UDPProtocolHandler
from ..security.auth import Authenticator
from ..security.tls_utils import create_client_ssl_context
from .constants import RECONNECT_DELAY
from .input import GamepadInput

logger = get_logger(__name__)


class UDPClientProtocol(asyncio.DatagramProtocol):
    """Datagram protocol that queues incoming packets"""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        self.queue.put_nowait(data)

    def error_received(self, exc: Exception) -> None:  # type: ignore[override]
        logger.error(f"UDP client error received: {exc}")


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
    ) -> None:
        """Construct the client and configure networking"""
        self.server_ip = server_ip
        self.server_port = server_port
        self.protocol = protocol.lower()
        self.gamepad = gamepad
        self.update_rate = update_rate
        self.config = config
        self.enable_tls = enable_tls and self.protocol == 'tcp'
        self.ssl_context: Optional[ssl.SSLContext] = None

        # Security
        self.authenticator = Authenticator(password)

        # Initialize TLS if enabled
        if self.enable_tls:
            try:
                self.ssl_context = create_client_ssl_context(verify_cert=False)
                logger.info("TLS/SSL encryption enabled")
            except Exception as e:
                logger.error(f"Failed to initialize TLS: {e}")
                logger.warning("Continuing without TLS encryption")
                self.enable_tls = False
        else:
            if self.protocol == 'tcp':
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
        self.main_task = None
        self.heartbeat_task = None
        
        logger.info(f"Client initialized with {self.protocol.upper()} protocol")
        logger.info(f"Server: {self.server_ip}:{self.server_port}")
        logger.info(f"Update rate: {self.update_rate} Hz")
    
    async def run(self) -> bool:
        """Run the client using the chosen protocol"""
        self.running = True
        
        try:
            if self.protocol == 'tcp':
                await self._run_tcp()
            else:
                await self._run_udp()
            return True
        except asyncio.CancelledError:
            logger.info("Client cancelled")
            return False
        except Exception as e:
            logger.error(f"Client error: {e}")
            return False
        finally:
            self.running = False
    
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
        if self.main_task and not self.main_task.done():
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup gamepad
        self.gamepad.cleanup()
        
        logger.info("Shutdown complete")
        return True
    
    async def _run_tcp(self) -> None:
        """Main loop for TCP mode"""
        while not self.shutdown_event.is_set():
            try:
                # Connect to server
                logger.info(f"Connecting to TCP server at {self.server_ip}:{self.server_port}...")
                reader, writer = await asyncio.open_connection(
                    self.server_ip,
                    self.server_port,
                    ssl=self.ssl_context if self.enable_tls else None,
                    server_hostname=self.server_ip if self.enable_tls else None,
                )

                logger.info(f"Connected to server at {self.server_ip}:{self.server_port}")

                # Log TLS connection details if enabled
                if self.enable_tls:
                    ssl_object = writer.get_extra_info('ssl_object')
                    if ssl_object:
                        cipher = ssl_object.cipher()
                        tls_version = ssl_object.version()
                        logger.info(f"TLS handshake successful")
                        logger.debug(f"TLS connection details:")
                        logger.debug(f"  TLS version: {tls_version}")
                        if cipher:
                            logger.debug(f"  Cipher: {cipher[0]} (bits: {cipher[2]})")
                            logger.debug(f"  Protocol: {cipher[1]}")
                    else:
                        logger.warning(f"TLS enabled but no SSL object found")

                # Initialize protocol handler
                tcp_handler = TCPProtocolHandler(reader, writer)
                
                # Optimize socket settings
                sock = writer.get_extra_info('socket')
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                
                # Authenticate
                if not await self._tcp_auth(tcp_handler):
                    logger.error("Authentication failed, retrying in 5 seconds...")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
                
                # Start heartbeat task
                self.heartbeat_task = asyncio.create_task(
                    self._tcp_heartbeat_loop(tcp_handler)
                )
                
                # Set connection state
                self.connected = True
                
                # Main sending loop
                send_interval = 1.0 / self.update_rate
                last_send_time = time.time()
                batch_counter = 0
                
                while not self.shutdown_event.is_set():
                    # Poll gamepad and send update
                    message = self.gamepad.poll()
                    if message:
                        # Strip unnecessary fields to reduce message size
                        if batch_counter % 10 != 0:  # Only include full data every 10th message
                            if "timestamp" in message:
                                del message["timestamp"]
                        
                        batch_counter += 1
                        if not await tcp_handler.send_message(message):
                            break
                        if not await tcp_handler.drain():
                            break
                        if tcp_handler.writer.is_closing():
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
                            logger.error(f"Heartbeat task failed: {self.heartbeat_task.exception()}")
                        else:
                            logger.warning("Heartbeat task ended")
                        break
                
            except asyncio.CancelledError:
                logger.info("TCP send loop cancelled")
                break
            except Exception as e:
                logger.error(f"TCP connection error: {e}")
            
            # Update connection state
            self.connected = False
            
            # Cleanup
            try:
                if 'tcp_handler' in locals():
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
            challenge_msg = await tcp_handler.read_message()
            if not challenge_msg or challenge_msg.get("type") != "auth_challenge":
                logger.error("Authentication protocol error: Invalid challenge")
                return False

            logger.debug("Received authentication challenge")

            # Extract challenge and verify protocol version
            challenge = challenge_msg.get("challenge")
            salt = challenge_msg.get("salt")
            iterations = challenge_msg.get("iterations")
            if salt and iterations:
                logger.debug(f"Updating authenticator parameters (iterations: {iterations})")
                self.authenticator.set_parameters(salt, int(iterations))
            if challenge_msg.get("protocol_version") != PROTOCOL_VERSION:
                logger.error(f"Protocol version mismatch: server={challenge_msg.get('protocol_version')}, client={PROTOCOL_VERSION}")
                return False

            # Calculate HMAC response
            logger.debug("Generating authentication response")
            response = self.authenticator.generate_tcp_response(challenge)

            # Send auth response
            logger.debug("Sending authentication response")
            auth_response = {
                "type": "auth_response",
                "protocol_version": PROTOCOL_VERSION,
                "response": response
            }
            await tcp_handler.send_message(auth_response)
            await tcp_handler.drain()

            # Wait for auth result
            logger.debug("Waiting for authentication result")
            result = await tcp_handler.read_message()
            if not result:
                return False

            if result.get("type") == "auth_success":
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('message', 'Unknown error')}")
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
                    "timestamp": datetime.now().isoformat()
                }
                await tcp_handler.send_message(heartbeat)
                await tcp_handler.drain()
                
                # Wait for heartbeat acknowledgment with timeout
                try:
                    response = await asyncio.wait_for(tcp_handler.read_message(), timeout=5.0)
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
    
    async def _run_udp(self) -> None:
        """Main loop for UDP mode"""
        loop = asyncio.get_running_loop()

        while not self.shutdown_event.is_set():
            try:
                protocol = UDPClientProtocol()
                transport, _ = await loop.create_datagram_endpoint(
                    lambda: protocol,
                    remote_addr=(self.server_ip, self.server_port)
                )

                # Initialize UDP handler
                udp_handler = UDPProtocolHandler(transport, (self.server_ip, self.server_port))

                logger.info(f"UDP client sending to {self.server_ip}:{self.server_port}")

                # Set connection state
                self.connected = True

                # Retrieve hashing parameters if the client only has the plaintex
                # password. If the server does not respond, fall back to using
                # the plaintext key.
                if self.authenticator.password_plain:
                    req = {
                        "type": "auth_params_request",
                        "protocol_version": PROTOCOL_VERSION,
                        "timestamp": datetime.now().isoformat(),
                    }
                    udp_handler.send_message(req)
                    try:
                        data = await asyncio.wait_for(protocol.queue.get(), timeout=0.2)
                    except asyncio.TimeoutError:
                        logger.debug("No auth parameters received; assuming plaintext mode")
                    else:
                        resp = json.loads(data.decode("utf-8"))
                        if resp.get("type") == "auth_params":
                            salt = resp.get("salt")
                            iterations = resp.get("iterations")
                            if salt and iterations is not None:
                                self.authenticator.set_parameters(str(salt), int(iterations))
                                # Use the derived key for tokens
                                self.authenticator.password_plain = None


                last_heartbeat = time.time()
                send_interval = 1.0 / self.update_rate

                while not self.shutdown_event.is_set():
                    try:
                        current_time = time.time()

                        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
                            heartbeat = {
                                "type": "heartbeat",
                                "protocol_version": PROTOCOL_VERSION,
                                "timestamp": datetime.now().isoformat(),
                            }
                            auth_token = self.authenticator.generate_udp_token()
                            if auth_token:
                                heartbeat["auth_token"] = auth_token

                            udp_handler.send_message(heartbeat)

                            try:
                                data = await asyncio.wait_for(protocol.queue.get(), timeout=5.0)
                                response = json.loads(data.decode("utf-8"))
                                if response.get("type") != "heartbeat_ack":
                                    logger.warning("Invalid heartbeat response")
                                    raise ConnectionError("Invalid heartbeat ack")
                            except asyncio.TimeoutError:
                                logger.warning("Heartbeat acknowledgment timeout")
                                raise ConnectionError("Heartbeat timeout")

                            last_heartbeat = current_time

                        message = self.gamepad.poll()
                        if message:
                            auth_token = self.authenticator.generate_udp_token()
                            if auth_token:
                                message["auth_token"] = auth_token
                            udp_handler.send_message(message)

                        await asyncio.sleep(send_interval)

                    except asyncio.CancelledError:
                        logger.info("UDP send loop cancelled")
                        raise
                    except Exception as e:
                        logger.error(f"Error in UDP send loop: {e}")
                        raise

            except asyncio.CancelledError:
                logger.info("UDP client cancelled")
                break
            except Exception as e:
                logger.error(f"UDP endpoint error: {e}")
            finally:
                self.connected = False
                if 'udp_handler' in locals():
                    udp_handler.close()

            if not self.shutdown_event.is_set():
                logger.info(f"Reconnecting in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)
