"""Message types and validators for the PadRelay"""
import json
from datetime import datetime
from ..core.exceptions import ProtocolError
from ..core.logging_utils import get_logger
from .constants import PROTOCOL_VERSION

logger = get_logger(__name__)

class BaseMessage:
    """Base message class"""
    
    def __init__(self, msg_type):
        """Create a message of ``msg_type``"""
        self.data = {
            "type": msg_type,
            "protocol_version": PROTOCOL_VERSION,
            "timestamp": datetime.now().isoformat()
        }
    
    def to_json(self):
        """Return a JSON representation"""
        return json.dumps(self.data)
    
    def to_bytes(self):
        """Return a UTF-8 encoded bytes object"""
        return self.to_json().encode('utf-8')
    
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
        elif msg_type == "auth_params_request":
            return AuthParamsRequestMessage.from_dict(data)
        elif msg_type == "auth_params":
            return AuthParamsMessage.from_dict(data)
        elif msg_type == "error":
            return ErrorMessage.from_dict(data)
        else:
            # Default to generic base message
            msg = cls("unknown")
            msg.data = data
            return msg


class InputMessage(BaseMessage):
    """Gamepad state message"""
    
    def __init__(self, buttons=None, axes=None, hats=None, triggers=None):
        """Create an input message."""
        super().__init__("input")
        self.data["buttons"] = buttons or []
        self.data["axes"] = axes or []
        self.data["hats"] = hats or []
        if triggers:
            self.data["triggers"] = triggers
    
    @classmethod
    def from_dict(cls, data):
        """Build an input message from ``data``"""
        msg = cls(
            buttons=data.get("buttons", []),
            axes=data.get("axes", []),
            hats=data.get("hats", []),
            triggers=data.get("triggers")
        )
        # Copy any extra fields
        for key, value in data.items():
            if key not in msg.data:
                msg.data[key] = value
        return msg


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


class AuthParamsRequestMessage(BaseMessage):
    """Client request for hashing parameters"""

    def __init__(self):
        super().__init__("auth_params_request")

    @classmethod
    def from_dict(cls, data):
        msg = cls()
        for key, value in data.items():
            if key not in msg.data:
                msg.data[key] = value
        return msg


class AuthParamsMessage(BaseMessage):
    """Server reply with salt and iterations"""

    def __init__(self, salt: str, iterations: int):
        super().__init__("auth_params")
        self.data["salt"] = salt
        self.data["iterations"] = iterations

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("salt", ""), int(data.get("iterations", 0)))


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
        if message.get("type") != "input":
            return False
            
        # Validate buttons (array of booleans)
        buttons = message.get("buttons", [])
        if not isinstance(buttons, list) or not all(isinstance(b, bool) for b in buttons):
            return False
            
        # Validate axes (array of floats between -1.0 and 1.0)
        axes = message.get("axes", [])
        if not isinstance(axes, list) or not all(isinstance(a, (int, float)) for a in axes):
            return False
        if not all(-1.0 <= a <= 1.0 for a in axes):
            return False
            
        # If triggers are present, validate them (floats between 0.0 and 1.0)
        triggers = message.get("triggers", [])
        if triggers and (not isinstance(triggers, list) or 
                         not all(isinstance(t, (int, float)) for t in triggers) or
                         not all(0.0 <= t <= 1.0 for t in triggers)):
            return False
            
        # If hats are present, validate them (tuples of -1, 0, or 1)
        hats = message.get("hats", [])
        if hats and (not isinstance(hats, list) or 
                     not all(isinstance(h, tuple) and len(h) == 2 for h in hats) or
                     not all(-1 <= x <= 1 and -1 <= y <= 1 for x, y in hats)):
            return False
            
        return True
        
    except Exception:
        return False
