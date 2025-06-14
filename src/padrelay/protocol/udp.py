"""UDP protocol utilities for the PadRelay"""
import asyncio
import json
from datetime import datetime
import hmac
import hashlib
from ..core.logging_utils import get_logger
from .constants import PROTOCOL_VERSION, MAX_MESSAGE_SIZE

logger = get_logger(__name__)

class UDPProtocolHandler:
    """Handle UDP communication on the client"""
    
    def __init__(self, transport=None, remote_addr=None):
        """Initialize with optional transport and address"""
        self.transport = transport
        self.remote_addr = remote_addr
    
    def send_message(self, message):
        """Send a UDP message"""
        try:
            if isinstance(message, dict):
                data = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                data = message.encode('utf-8')
            else:
                data = message
                
            if len(data) > MAX_MESSAGE_SIZE:
                logger.warning(f"Message too large for UDP: {len(data)} bytes")
                return False
                
            self.transport.sendto(data, self.remote_addr)
            return True
        except Exception as e:
            logger.error(f"Error sending UDP message: {e}")
            return False
    
    def close(self):
        """Close the UDP transport"""
        if self.transport:
            try:
                self.transport.close()
            except Exception as e:
                logger.error(f"Error closing UDP transport: {e}")


class UDPServerProtocol(asyncio.DatagramProtocol):
    """UDP server protocol"""
    def __init__(self, gamepad_handler, authenticator=None, tracker=None):
        """Create the server protocol"""
        self.gamepad_handler = gamepad_handler
        self.authenticator = authenticator
        self.tracker = tracker
        self.transport = None

    def connection_made(self, transport):
        """Called when the socket is ready"""
        self.transport = transport
        sockname = transport.get_extra_info('sockname')
        logger.info(f"UDP server listening on {sockname}")

    def datagram_received(self, data, addr):
        """Handle an incoming datagram"""
        # Apply rate limiting if enabled
        if self.tracker:
            was_blocked = self.tracker.is_blocked(addr)
            if self.tracker.is_rate_limited(addr):
                if not was_blocked:
                    logger.warning(f"Rate limit exceeded for UDP client {addr}")
                return
            
        # Decode message
        try:
            message = json.loads(data.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from {addr}: {e}")
            return
            
        # Check protocol version
        if message.get("protocol_version") != PROTOCOL_VERSION:
            logger.warning(f"Protocol version mismatch in UDP message from {addr}")
            return

        # Handle auth params request before authentication. Only reply if the
        # server expects hashed tokens (no plaintext password stored).
        if message.get("type") == "auth_params_request":
            if (
                self.authenticator
                and self.authenticator.password_plain is None
                and self.authenticator.password_hash
            ):
                resp = {
                    "type": "auth_params",
                    "protocol_version": PROTOCOL_VERSION,
                    "salt": self.authenticator.salt,
                    "iterations": self.authenticator.iterations,
                    "timestamp": datetime.now().isoformat(),
                }
                self.transport.sendto(json.dumps(resp).encode("utf-8"), addr)
            return
            
        # Authenticate if authenticator is provided
        if self.authenticator:
            if not self.authenticator.authenticate_udp(message):
                logger.warning(f"Invalid auth token in UDP message from {addr}")
                return
                
        # Process heartbeat
        if message.get("type") == "heartbeat":
            ack = {
                "type": "heartbeat_ack",
                "protocol_version": PROTOCOL_VERSION,
                "timestamp": datetime.now().isoformat()
            }
            self.transport.sendto(json.dumps(ack).encode('utf-8'), addr)
            return
            
        # Process input message
        if message.get("type") == "input":
            from .messages import validate_input_message
            if not validate_input_message(message):
                logger.warning(f"Invalid UDP message format from {addr}")
                return
                
            self.gamepad_handler.process(message)
        else:
            logger.warning(f"Unknown UDP message type from {addr}: {message.get('type')}")

    def error_received(self, exc: Exception) -> None:
        """Called when a send or receive operation fails"""
        logger.error(f"UDP error: {exc}")

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the connection is closed"""
        logger.info("UDP connection lost")
