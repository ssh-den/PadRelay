"""
Authentication utilities for the PadRelay
"""

import asyncio
import hashlib
import hmac
import secrets
from typing import Optional

from ..core.logging_utils import get_logger

logger = get_logger(__name__)


class Authenticator:
    """Authentication handler for both client and server"""

    PBKDF2_PREFIX = "pbkdf2_sha256"
    DEFAULT_ITERATIONS = 100000
    MIN_ITERATIONS = 100000
    MAX_ITERATIONS = 600000
    MAX_SALT_LENGTH = 128

    def __init__(self, password: Optional[str] = None) -> None:
        """
        Initialize an authenticator

        Args:
            password: Plaintext password or encoded PBKDF2 hash (optional)
        """
        self.password_plain: Optional[str] = None
        self.salt: Optional[str] = None
        self.iterations: int = self.DEFAULT_ITERATIONS
        self.password_hash: Optional[str] = None

        if password:
            if self._is_hash_string(password):
                self.iterations, self.salt, self.password_hash = (
                    self._parse_hash_string(password)
                )
            else:
                self.password_plain = password
                self.salt = secrets.token_hex(16)
                self.password_hash = self._hash_password(
                    password, self.salt, self.iterations
                )

    @staticmethod
    def validate_parameters(salt: str, iterations: int) -> None:
        """Reject unsupported PBKDF2 work factors and salt sizes before hashing."""
        if (
            type(iterations) is not int
            or not Authenticator.MIN_ITERATIONS
            <= iterations
            <= Authenticator.MAX_ITERATIONS
            or not isinstance(salt, str)
            or not 16 <= len(salt) <= Authenticator.MAX_SALT_LENGTH
            or not salt.isascii()
        ):
            raise ValueError("Invalid or excessive PBKDF2 parameters")

    def set_parameters(self, salt: str, iterations: int) -> None:
        self.validate_parameters(salt, iterations)
        digest = (
            self._hash_password(self.password_plain, salt, iterations)
            if self.password_plain
            else self.password_hash
        )
        self.salt, self.iterations, self.password_hash = salt, iterations, digest

    async def set_parameters_async(self, salt: str, iterations: int) -> None:
        """Validate before scheduling; commit only after completed derivation."""
        self.validate_parameters(salt, iterations)
        digest = self.password_hash
        if self.password_plain:
            digest = await asyncio.to_thread(
                self._hash_password, self.password_plain, salt, iterations
            )
        self.salt, self.iterations, self.password_hash = salt, iterations, digest

    @staticmethod
    def _is_hash_string(value: str) -> bool:
        return value.startswith(Authenticator.PBKDF2_PREFIX + "$")

    @staticmethod
    def _parse_hash_string(value: str) -> tuple[int, str, str]:
        parts = value.split("$")
        if len(parts) != 4 or parts[0] != Authenticator.PBKDF2_PREFIX:
            raise ValueError("Invalid hash string")
        iterations = int(parts[1])
        salt = parts[2]
        pw_hash = parts[3]
        Authenticator.validate_parameters(salt, iterations)
        if len(pw_hash) != 64 or len(bytes.fromhex(pw_hash)) != 32:
            raise ValueError("Invalid password hash")
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
        Authenticator.validate_parameters(salt, iterations)
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), iterations
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
            key.encode(), challenge.encode(), hashlib.sha256
        ).hexdigest()

        return (
            isinstance(response, str)
            and response.isascii()
            and hmac.compare_digest(response, expected_hmac)
        )

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

        return hmac.new(key.encode(), challenge.encode(), hashlib.sha256).hexdigest()
