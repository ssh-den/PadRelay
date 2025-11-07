"""Server application for the PadRelay"""
import asyncio
import socket
import ssl
import gc
import secrets
import weakref
from pathlib import Path
from typing import Optional
from datetime import datetime
from ..core.logging_utils import get_logger
from ..core.exceptions import AuthenticationError
from ..protocol.constants import HEARTBEAT_INTERVAL
from ..protocol.tcp import TCPProtocolHandler
from ..protocol.udp import UDPServerProtocol
from ..security.auth import Authenticator
from ..security.rate_limiting import ConnectionTracker
from ..security.tls_utils import create_server_ssl_context, warn_if_cert_expiring_soon
from .virtual_gamepad import VirtualGamepad
from .input_processor import GamepadHandler
from .constants import (
    MAX_CONNECTIONS,
    DEFAULT_BLOCK_DURATION,
)

logger = get_logger(__name__)

class VirtualGamepadServer:
    """Server controller"""
    
    def __init__(
        self,
        host,
        port,
        password,
        gamepad_type='xbox360',
        config=None,
        rate_limit_window=60,
        max_requests=100,
        block_duration=DEFAULT_BLOCK_DURATION,
        protocol='tcp',
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
            enable_tls: Enable TLS/SSL encryption for TCP connections
            cert_path: Path to TLS certificate (optional)
            key_path: Path to TLS private key (optional)
        """
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.config = config
        self.password = password
        self.enable_tls = enable_tls and self.protocol == 'tcp'
        self.cert_path = cert_path
        self.key_path = key_path
        self.ssl_context: Optional[ssl.SSLContext] = None
        
        # Initialize active clients tracking
        self.active_clients = set()
        self.server = None
        
        # Security
        self.authenticator = Authenticator(password)
        self.tracker = ConnectionTracker(
            max_connections=MAX_CONNECTIONS,
            rate_limit_window=rate_limit_window,
            max_requests=max_requests,
            block_duration=block_duration,
        )
        
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

        # Initialize TLS if enabled
        if self.enable_tls:
            try:
                self.ssl_context = create_server_ssl_context(self.cert_path, self.key_path, auto_generate=True)
                if self.ssl_context:
                    logger.info("TLS/SSL encryption enabled")
                    warn_if_cert_expiring_soon(self.cert_path)
                else:
                    logger.error("Failed to create SSL context, continuing without TLS")
                    self.enable_tls = False
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
            if self.protocol == 'udp':
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
            
        # Reset gamepad state
        self.virtual_gamepad.reset_gamepad_state()
            
        logger.info("All connections closed")
        return True
    
    async def _run_tcp_server(self) -> None:
        """Start the TCP server"""
        try:
            server = await asyncio.start_server(
                self._handle_tcp_client,
                self.host,
                self.port,
                ssl=self.ssl_context if self.enable_tls else None,
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
            if e.errno == 98 or e.errno == 10048:  # Address already in use (Linux/Windows)
                logger.error(f"Port {self.port} is already in use. Choose a different port or stop the other server.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting TCP server: {e}")
            raise
    
    async def _handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a TCP client

        Args:
            reader: asyncio.StreamReader object
            writer: asyncio.StreamWriter object
        """
        addr = writer.get_extra_info('peername')
        logger.info(f"New TCP connection from {addr}")

        # Log TLS connection details if enabled
        if self.enable_tls:
            ssl_object = writer.get_extra_info('ssl_object')
            if ssl_object:
                cipher = ssl_object.cipher()
                tls_version = ssl_object.version()
                logger.info(f"TLS connection established from {addr}")
                logger.debug(f"TLS handshake details:")
                logger.debug(f"  TLS version: {tls_version}")
                if cipher:
                    logger.debug(f"  Cipher: {cipher[0]} (bits: {cipher[2]})")
                    logger.debug(f"  Protocol: {cipher[1]}")
            else:
                logger.warning(f"TLS enabled but no SSL object found for connection from {addr}")

        # Initialize protocol handler
        tcp_handler = TCPProtocolHandler(reader, writer)
        
        # Optimize TCP socket configuration
        sock = writer.get_extra_info('socket')
        if sock:
            # Disable Nagle algorithm to reduce latency
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Increase socket buffer sizes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        
        # Check connection limit
        if not self.tracker.can_connect(addr):
            logger.warning(f"Connection limit exceeded for {addr}")
            await tcp_handler.send_message({
                "type": "error",
                "protocol_version": "1.0",
                "message": "Another client is already connected."
            })
            await tcp_handler.drain()
            tcp_handler.close()
            await tcp_handler.wait_closed()
            return
            
        # Perform authentication if password is set
        authenticated = False
        if self.password:
            # Authentication
            try:
                challenge = secrets.token_hex(16)
                logger.debug(f"Sending authentication challenge to {addr}")
                auth_challenge = {
                    "type": "auth_challenge",
                    "protocol_version": "1.0",
                    "challenge": challenge,
                    "salt": self.authenticator.salt,
                    "iterations": self.authenticator.iterations,
                }
                await tcp_handler.send_message(auth_challenge)
                await tcp_handler.drain()
                
                # Wait for response with shorter timeout
                try:
                    auth_response = await asyncio.wait_for(tcp_handler.read_message(), timeout=5.0)
                    if not auth_response:
                        logger.warning(f"Authentication failed for {addr}: no response")
                        tcp_handler.close()
                        return
                
                    # Verify protocol and response type
                    if (auth_response.get("protocol_version") != "1.0" or
                        auth_response.get("type") != "auth_response" or
                        "response" not in auth_response):
                        logger.warning(f"Invalid authentication response from {addr}")
                        await tcp_handler.send_message({
                            "type": "error",
                            "protocol_version": "1.0",
                            "message": "Invalid authentication response"
                        })
                        await tcp_handler.drain()
                        tcp_handler.close()
                        return
                    
                    # Verify HMAC
                    logger.debug(f"Verifying authentication response from {addr}")
                    if not self.authenticator.verify_tcp_response(challenge, auth_response["response"]):
                        logger.warning(f"Failed authentication attempt from {addr}")
                        await tcp_handler.send_message({
                            "type": "auth_failed",
                            "protocol_version": "1.0",
                            "message": "Authentication failed"
                        })
                        await tcp_handler.drain()
                        tcp_handler.close()
                        return

                    # Authentication successful
                    logger.debug(f"Authentication successful for {addr}")
                    await tcp_handler.send_message({
                        "type": "auth_success",
                        "protocol_version": "1.0"
                    })
                    await tcp_handler.drain()
                    authenticated = True
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Authentication timeout for {addr}")
                    tcp_handler.close()
                    return
            except Exception as e:
                logger.error(f"Authentication error for {addr}: {e}")
                tcp_handler.close()
                return
        else:
            # No authentication required
            authenticated = True
        
        # Mark client as authenticated
        if authenticated:
            self.tracker.authenticate(addr)
            
            # Add this client to active clients list for clean shutdown
            self.active_clients.add(writer)
        
        # Process messages - optimized for performance
        try:
            # Rate limiting state
            last_rate_check = datetime.now().timestamp()
            message_count = 0
            max_rate = 1000  # messages per second
            
            # Message processing state
            last_heartbeat = datetime.now().timestamp()
            validation_interval = 10  # Only validate every N messages
            validation_counter = 0
            
            while not self.shutdown_event.is_set():
                # Wait for message with longer timeout to reduce CPU usage
                try:
                    msg = await asyncio.wait_for(tcp_handler.read_message(), timeout=HEARTBEAT_INTERVAL)
                    if not msg:
                        logger.info(f"Connection closed by {addr}")
                        break
                except asyncio.TimeoutError:
                    logger.info(f"Heartbeat timeout for {addr}")
                    break
                
                # Simple rate limiting
                message_count += 1
                current_time = datetime.now().timestamp()
                if current_time - last_rate_check > 1.0:
                    rate = message_count / (current_time - last_rate_check)
                    if rate > max_rate:
                        await asyncio.sleep(0.01)  # Small delay if rate is too high
                    message_count = 0
                    last_rate_check = current_time
                
                # Handle heartbeat
                if msg.get("type") == "heartbeat":
                    await tcp_handler.send_message({
                        "type": "heartbeat_ack",
                        "protocol_version": "1.0",
                        "timestamp": datetime.now().isoformat()
                    })
                    # Only drain for heartbeats
                    await tcp_handler.drain()
                    last_heartbeat = current_time
                    continue
                
                # Handle input message - with optimized validation
                if msg.get("type") == "input":
                    validation_counter += 1
                    
                    # Only validate every N messages to improve performance
                    if validation_counter >= validation_interval:
                        from ..protocol.messages import validate_input_message
                        if not validate_input_message(msg):
                            logger.warning(f"Invalid message format from {addr}")
                            validation_counter = 0
                            continue
                        validation_counter = 0
                    
                    # Process the message using the handler
                    self.gamepad_handler.process(msg)
                
            logger.info(f"Client {addr} disconnected from main loop")
                    
        except ConnectionResetError:
            logger.info(f"Connection reset by {addr}")
        except Exception as e:
            logger.error(f"Error handling connection from {addr}: {e}")
        finally:
            # Clean up
            if writer in self.active_clients:
                self.active_clients.remove(writer)
                
            try:
                tcp_handler.close()
                await tcp_handler.wait_closed()
            except Exception as e:  # pragma: no cover - safety net
                logger.error(f"Error closing TCP handler: {e}")
                
            # Update tracker and reset gamepad
            self.tracker.disconnect(addr)
            self.virtual_gamepad.reset_gamepad_state()
            logger.info(f"Connection closed for {addr}")
            
            # Release references to encourage garbage collection
            gc.collect()
    
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
        """Start the UDP server"""
        try:
            loop = asyncio.get_running_loop()
            
            # Create UDP protocol with the gamepad handler
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UDPServerProtocol(
                    self.gamepad_handler,
                    self.authenticator,
                    self.tracker
                ),
                local_addr=(self.host, self.port)
            )
            
            logger.info(f"UDP server listening on {self.host}:{self.port}")
            
            # Store transport for cleanup
            self.transport = transport
            
            try:
                await self.shutdown_event.wait()
            finally:
                transport.close()
                
        except OSError as e:
            logger.error(f"Failed to start UDP server: {e}")
            # Check if the port is already in use
            if e.errno == 98 or e.errno == 10048:  # Address already in use (Linux/Windows)
                logger.error(f"Port {self.port} is already in use. Choose a different port or stop the other server.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting UDP server: {e}")
            raise
