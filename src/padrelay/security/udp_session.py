"""TLS-provisioned one-way AES-GCM datagrams with bounded replay state."""

import json
import secrets
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..protocol.constants import MAX_MESSAGE_SIZE


class UDPSession:
    """Encrypt client input with a fresh key from its TLS control connection."""

    MAGIC = b"PRU2"
    HEADER_SIZE = 28
    WINDOW = 64
    LIFETIME = 600
    MAX_SEQUENCE = 2**32

    def __init__(self, session_id: bytes, key: bytes, peer_ip: str = "") -> None:
        if len(session_id) != 16 or len(key) != 32:
            raise ValueError("Invalid UDP session material")
        self.session_id = session_id
        self.key = key
        self.peer_ip = peer_ip
        self.expires_at = time.monotonic() + self.LIFETIME
        self.send_sequence = 0
        self.highest_received = -1
        self.received_bitmap = 0
        self.cipher = AESGCM(key)

    @classmethod
    def create(cls, peer_ip: str) -> "UDPSession":
        return cls(
            secrets.token_bytes(16), AESGCM.generate_key(bit_length=256), peer_ip
        )

    def parameters(self) -> dict:
        """Send only inside the authenticated TLS control stream."""
        return {
            "version": 2,
            "session_id": self.session_id.hex(),
            "key": self.key.hex(),
        }

    @classmethod
    def from_parameters(cls, parameters: dict) -> "UDPSession":
        if parameters.get("version") != 2:
            raise ValueError("UDP protocol 2 is required")
        return cls(
            bytes.fromhex(parameters["session_id"]), bytes.fromhex(parameters["key"])
        )

    def encode(self, message: dict) -> bytes:
        if (
            time.monotonic() >= self.expires_at
            or self.send_sequence >= self.MAX_SEQUENCE
        ):
            raise ValueError("UDP session expired")
        sequence = self.send_sequence
        self.send_sequence += 1  # Never reuse a nonce, including failed sends.
        header = self.MAGIC + self.session_id + sequence.to_bytes(8, "big")
        payload = json.dumps(message, allow_nan=False, separators=(",", ":")).encode()
        if len(payload) + self.HEADER_SIZE + 16 > MAX_MESSAGE_SIZE:
            raise ValueError("UDP message too large")
        return header + self.cipher.encrypt(
            sequence.to_bytes(12, "big"), payload, header
        )

    def decode(self, packet: bytes) -> dict | None:
        if (
            time.monotonic() >= self.expires_at
            or len(packet) < self.HEADER_SIZE + 16
            or len(packet) > MAX_MESSAGE_SIZE
            or packet[:20] != self.MAGIC + self.session_id
        ):
            return None
        sequence = int.from_bytes(packet[20:28], "big")
        if sequence >= self.MAX_SEQUENCE:
            return None
        offset = self.highest_received - sequence
        if offset >= self.WINDOW or (
            offset >= 0 and self.received_bitmap & (1 << offset)
        ):
            return None
        try:
            payload = self.cipher.decrypt(
                sequence.to_bytes(12, "big"), packet[28:], packet[:28]
            )
            message = json.loads(payload)
        except (InvalidTag, ValueError, UnicodeDecodeError, RecursionError):
            return None
        if not isinstance(message, dict):
            return None
        # Commit replay state only after authenticating the entire packet.
        if sequence > self.highest_received:
            shift = min(sequence - self.highest_received, self.WINDOW)
            self.received_bitmap = ((self.received_bitmap << shift) | 1) & (
                (1 << self.WINDOW) - 1
            )
            self.highest_received = sequence
        else:
            self.received_bitmap |= 1 << offset
        return message
