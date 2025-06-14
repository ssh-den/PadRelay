"""Exception hierarchy for the PadRelay"""

from typing import Any, Optional

class GamepadBridgeError(Exception):
    """Base exception for bridge errors"""
    
    def __init__(self, message: str = "An error occurred in the PadRelay", details: Optional[Any] = None) -> None:

        self.message = message
        self.details = details
        super().__init__(self.message)
        
    def __str__(self) -> str:

        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ProtocolError(GamepadBridgeError):
    """Protocol-related error"""
    
    def __init__(self, message: str = "Protocol error", details: Optional[Any] = None, protocol_version: Optional[str] = None) -> None:

        self.protocol_version = protocol_version
        super().__init__(message, details)
        
    def __str__(self) -> str:

        base_str = super().__str__()
        if self.protocol_version:
            return f"{base_str} (Protocol version: {self.protocol_version})"
        return base_str


class AuthenticationError(GamepadBridgeError):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None, addr: Optional[str] = None) -> None:

        self.addr = addr
        super().__init__(message, details)
        
    def __str__(self) -> str:

        base_str = super().__str__()
        if self.addr:
            return f"{base_str} (Client: {self.addr})"
        return base_str


class ConnectionError(GamepadBridgeError):
    """Connection related error"""
    
    def __init__(self, message: str = "Connection error", details: Optional[Any] = None, addr: Optional[str] = None, reconnect_attempt: Optional[int] = None) -> None:

        self.addr = addr
        self.reconnect_attempt = reconnect_attempt
        super().__init__(message, details)
        
    def __str__(self) -> str:

        base_str = super().__str__()
        if self.addr:
            base_str = f"{base_str} (Remote: {self.addr})"
        if self.reconnect_attempt is not None:
            base_str = f"{base_str} (Reconnect attempt: {self.reconnect_attempt})"
        return base_str


class ConfigurationError(GamepadBridgeError):
    """Configuration problem"""
    
    def __init__(self, message: str = "Configuration error", details: Optional[Any] = None, config_file: Optional[str] = None, setting: Optional[str] = None) -> None:

        self.config_file = config_file
        self.setting = setting
        super().__init__(message, details)
        
    def __str__(self) -> str:

        base_str = super().__str__()
        if self.config_file:
            base_str = f"{base_str} (File: {self.config_file})"
        if self.setting:
            base_str = f"{base_str} (Setting: {self.setting})"
        return base_str


class InputError(GamepadBridgeError):
    """Gamepad input error"""
    
    def __init__(self, message: str = "Input error", details: Optional[Any] = None, input_type: Optional[str] = None, input_value: Optional[Any] = None) -> None:

        self.input_type = input_type
        self.input_value = input_value
        super().__init__(message, details)
        
    def __str__(self) -> str:
        
        base_str = super().__str__()
        if self.input_type:
            base_str = f"{base_str} (Input type: {self.input_type})"
        if self.input_value is not None:
            base_str = f"{base_str} (Value: {self.input_value})"
        return base_str
