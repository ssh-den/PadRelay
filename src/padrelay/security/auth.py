"""
Authentication utilities for the PadRelay
"""
import hashlib
import hmac
import secrets
import time
from typing import Optional
from ..core.logging_utils import get_logger

logger = get_logger(__name__)

class Authenticator:
    """Authentication handler for both client and server"""
    
    PBKDF2_PREFIX = "pbkdf2_sha256"
    DEFAULT_ITERATIONS = 100000
    UDP_TOKEN_TTL = 60  # seconds

    def __init__(self, password: Optional[str] = None) -> None:
        """
        Initialize an authenticator
        
        Args:
            password: Plain text password (optional)
            salt: Salt for password hashing (optional)
        """
        self.password_plain: Optional[str] = None
        self.salt: Optional[str] = None
        self.iterations: int = self.DEFAULT_ITERATIONS
        self.password_hash: Optional[str] = None

        if password:
            if self._is_hash_string(password):
                self.iterations, self.salt, self.password_hash = self._parse_hash_string(password)
            else:
                self.password_plain = password
                self.salt = secrets.token_hex(16)
                self.password_hash = self._hash_password(password, self.salt, self.iterations)

    def set_parameters(self, salt: str, iterations: int) -> None:
        """Set hashing parameters and recompute derived key if needed"""
        self.salt = salt
        self.iterations = iterations
        if self.password_plain:
            self.password_hash = self._hash_password(self.password_plain, salt, iterations)
    
    @staticmethod
    def _is_hash_string(value: str) -> bool:
        return value.startswith(Authenticator.PBKDF2_PREFIX + "$") and len(value.split("$")) == 4

    @staticmethod
    def _parse_hash_string(value: str) -> tuple[int, str, str]:
        parts = value.split("$")
        if len(parts) != 4 or parts[0] != Authenticator.PBKDF2_PREFIX:
            raise ValueError("Invalid hash string")
        iterations = int(parts[1])
        salt = parts[2]
        pw_hash = parts[3]
        return iterations, salt, pw_hash

    @staticmethod
    def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
        """Return a PBKDF2 hash string for a password"""
        salt = secrets.token_hex(16)
        digest = Authenticator._hash_password(password, salt, iterations)
        return f"{Authenticator.PBKDF2_PREFIX}${iterations}${salt}${digest}"

    @staticmethod
    def _hash_password(password: str, salt: str, iterations: int) -> str:
        """
        Hash password using PBKDF2.
        
        Args:
            password: Plain text password
            salt: Salt for hashing
            
        Returns:
            str: Hexadecimal digest of the hashed password
        """
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            iterations
        ).hex()

    def get_hash_string(self) -> Optional[str]:
        if self.password_hash and self.salt:
            return f"{self.PBKDF2_PREFIX}${self.iterations}${self.salt}${self.password_hash}"
        return None

    def verify_password(self, password: str) -> bool:
        if not self.password_hash or not self.salt:
            return False
        digest = self._hash_password(password, self.salt, self.iterations)
        return hmac.compare_digest(digest, self.password_hash)
    
    def generate_tcp_challenge(self) -> str:
        """
        Generate a challenge for TCP authentication
        
        Returns:
            str: Random challenge string
        """
        return secrets.token_hex(16)
    
    def verify_tcp_response(self, challenge: str, response: str) -> bool:
        """
        Verify a TCP authentication response
        
        Args:
            challenge: Challenge string
            response: HMAC response to verify
            
        Returns:
            bool: True if response is valid, False otherwise
        """
        
        key = self.password_hash or self.password_plain
        if not key:
            return True

        expected_hmac = hmac.new(
            key.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(response, expected_hmac)
    
    def generate_udp_token(self, current_time: Optional[int] = None) -> Optional[str]:
        """
        Generate a token for UDP authentication
        
        Returns:
            str: Authentication token
        """
        
        key = self.password_plain or self.password_hash

        if not key:
            return None

        if current_time is None:
            current_time = int(time.time())

        window = current_time // self.UDP_TOKEN_TTL

        return hmac.new(
            key.encode(),
            f"udp_auth{window}".encode(),
            hashlib.sha256
        ).hexdigest()
    
    def generate_tcp_response(self, challenge: str) -> str:
        """
        Generate a response to a TCP authentication challenge
        
        Args:
            challenge: Challenge string
            
        Returns:
            str: HMAC response
        """
        key = self.password_hash or self.password_plain

        if not key:
            return ""

        return hmac.new(
            key.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def authenticate_udp(self, message: dict, current_time: Optional[int] = None) -> bool:
        """
        Authenticate a UDP message
        
        Args:
            message: Message to authenticate
            
        Returns:
            bool: True if message is authenticated, False otherwise
        """
        key = self.password_plain or self.password_hash

        if not key:
            return True

        if current_time is None:
            current_time = int(time.time())

        token = message.get("auth_token")
        if not token:
            return False

        valid_tokens = [
            self.generate_udp_token(current_time=current_time),
            self.generate_udp_token(current_time=current_time - self.UDP_TOKEN_TTL),
        ]

        return token in valid_tokens
