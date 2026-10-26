"""Message types and validators for the PadRelay"""

import json
from datetime import datetime

from ..core.controller_state import InputState
from ..core.exceptions import ProtocolError
from ..core.logging_utils import get_logger
from .constants import PROTOCOL_VERSION

logger = get_logger(__name__)


class BaseMessage:
    """Base message class"""

    def __init__(self, msg_type, *, payload=None):
        """Create a message of ``msg_type``"""
        self.data = (
            payload
            if payload is not None
            else {
                "type": msg_type,
                "protocol_version": PROTOCOL_VERSION,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_json(self):
        """Return a JSON representation"""
        return json.dumps(self.data)

    def to_bytes(self):
        """Return a UTF-8 encoded bytes object"""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data):
        """Create a message from ``data``"""
        if not data or not isinstance(data, dict) or "type" not in data:
            raise ProtocolError("Invalid message data")

        msg_type = data["type"]

        # Create appropriate message type based on the 'type' field
        if msg_type == "input":
            return InputMessage.from_dict(data)
        elif msg_type == "heartbeat":
            return HeartbeatMessage.from_dict(data)
        elif msg_type == "heartbeat_ack":
            return HeartbeatAckMessage.from_dict(data)
        elif msg_type == "auth_challenge":
            return AuthChallengeMessage.from_dict(data)
        elif msg_type == "auth_response":
            return AuthResponseMessage.from_dict(data)
        elif msg_type == "auth_success":
            return AuthSuccessMessage.from_dict(data)
        elif msg_type == "auth_failed":
            return AuthFailedMessage.from_dict(data)
        elif msg_type == "error":
            return ErrorMessage.from_dict(data)
        else:
            # Default to generic base message
            msg = cls("unknown")
            msg.data = data
            return msg


class InputMessage(BaseMessage):
    """Serialize exactly one canonical state; physical layouts never reach the wire."""

    def __init__(self, state: InputState | None = None):
        super().__init__(
            "input", payload=(state if state is not None else InputState()).to_message()
        )

    @classmethod
    def from_dict(cls, data):
        return cls(InputState.from_message(data))


class HeartbeatMessage(BaseMessage):
    """Heartbeat ping"""

    def __init__(self):
        """Create a heartbeat message"""
        super().__init__("heartbeat")

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        msg = cls()
        # Copy any extra fields
        for key, value in data.items():
            if key not in msg.data:
                msg.data[key] = value
        return msg


class HeartbeatAckMessage(BaseMessage):
    """Heartbeat acknowledgment"""

    def __init__(self):
        """Create an acknowledgment message"""
        super().__init__("heartbeat_ack")

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        msg = cls()
        # Copy any extra fields
        for key, value in data.items():
            if key not in msg.data:
                msg.data[key] = value
        return msg


class AuthChallengeMessage(BaseMessage):
    """Authentication challenge"""

    def __init__(self, challenge):
        """Create a challenge with ``challenge`` string"""
        super().__init__("auth_challenge")
        self.data["challenge"] = challenge

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        return cls(data.get("challenge", ""))


class AuthResponseMessage(BaseMessage):
    """Authentication response"""

    def __init__(self, response):
        """Create a response containing ``response``"""
        super().__init__("auth_response")
        self.data["response"] = response

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        return cls(data.get("response", ""))


class AuthSuccessMessage(BaseMessage):
    """Authentication success"""

    def __init__(self):
        """Create a success message"""
        super().__init__("auth_success")

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        return cls()


class AuthFailedMessage(BaseMessage):
    """Authentication failed"""

    def __init__(self, message="Authentication failed"):
        """Create a failure message"""
        super().__init__("auth_failed")
        self.data["message"] = message

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        return cls(data.get("message", "Authentication failed"))


class ErrorMessage(BaseMessage):
    """Represents an error"""

    def __init__(self, message="Unknown error"):
        """Create an error message"""
        super().__init__("error")
        self.data["message"] = message

    @classmethod
    def from_dict(cls, data):
        """Build from ``data``"""
        return cls(data.get("message", "Unknown error"))


def validate_input_message(message):
    """Return ``True`` if ``message`` is a valid input payload"""
    try:
        InputState.from_message(message)
        return True
    except (ValueError, TypeError, OverflowError):
        return False
