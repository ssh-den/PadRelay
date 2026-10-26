"""UDP protocol utilities for the PadRelay"""

import asyncio
import json

from ..core.logging_utils import get_logger
from ..security.udp_session import UDPSession
from .constants import MAX_MESSAGE_SIZE, PROTOCOL_VERSION
from .messages import validate_input_message

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
            if self.transport is None:
                return False
            if isinstance(message, dict):
                data = json.dumps(message).encode("utf-8")
            elif isinstance(message, str):
                data = message.encode("utf-8")
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
    """Accept only encrypted input for a live TLS-authenticated session."""

    def __init__(self, gamepad_handler, sessions=None, tracker=None):
        self.gamepad_handler = gamepad_handler
        self.sessions = sessions if sessions is not None else {}
        self.tracker = tracker
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if self.tracker and self.tracker.is_rate_limited(addr):
            return
        if (
            self.transport is None
            or not 44 <= len(data) <= MAX_MESSAGE_SIZE
            or data[:4] != UDPSession.MAGIC
        ):
            return
        session = self.sessions.get(data[4:20])
        if session is None or session.peer_ip != addr[0]:
            return
        previous_sequence = session.highest_received
        message = session.decode(data)
        if (
            message is not None
            and session.highest_received > previous_sequence
            and message.get("protocol_version") == PROTOCOL_VERSION
            and validate_input_message(message)
        ):
            self.gamepad_handler.process(message)

    def error_received(self, exc: Exception) -> None:
        logger.debug(f"UDP error: {exc}")
