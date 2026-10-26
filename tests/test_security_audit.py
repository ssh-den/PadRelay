"""Password hashing, challenge-response, admission limits and input validation."""

import pytest

from padrelay.protocol.messages import validate_input_message
from padrelay.security.auth import Authenticator
from padrelay.security.rate_limiting import ConnectionTracker


class TestPasswordSecurity:
    """Test password hashing and storage security"""

    def test_pbkdf2_iterations_minimum(self):
        """Verify PBKDF2 uses minimum 100,000 iterations"""
        auth = Authenticator("test_password")
        assert auth.iterations >= 100000, "PBKDF2 iterations below security minimum"

    def test_password_hash_uniqueness(self):
        """Verify same password produces different hashes (unique salts)"""
        auth1 = Authenticator("same_password")
        auth2 = Authenticator("same_password")

        # Same password should produce different hashes due to unique salts
        assert auth1.salt != auth2.salt
        assert auth1.password_hash != auth2.password_hash

    def test_password_hash_format(self):
        """Check the PBKDF2 algorithm, iteration count, salt and digest fields."""
        auth = Authenticator("test_password")
        hash_string = auth.get_hash_string()

        # Format: pbkdf2_sha256$iterations$salt$digest
        parts = hash_string.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert int(parts[1]) >= 100000
        assert len(parts[2]) == 32  # 16-byte salt in hex
        assert len(parts[3]) == 64  # SHA256 digest in hex

    def test_tcp_hmac_accepts_valid_response_and_rejects_invalid_response(self):
        """Check response acceptance and rejection without making timing assertions."""
        auth = Authenticator("test_password")
        challenge = auth.generate_tcp_challenge()

        correct_response = auth.generate_tcp_response(challenge)
        wrong_response = "0" * 64  # Wrong response same length

        assert auth.verify_tcp_response(challenge, correct_response) is True
        assert auth.verify_tcp_response(challenge, wrong_response) is False


class TestAuthenticationSecurity:
    """Test authentication mechanism security"""

    def test_tcp_challenge_randomness(self):
        """Verify TCP challenges are cryptographically random"""
        auth = Authenticator("test_password")

        # Generate multiple challenges
        challenges = [auth.generate_tcp_challenge() for _ in range(100)]

        # All should be unique (32 hex chars = 128 bits of entropy)
        assert len(set(challenges)) == 100, "Challenge collision detected"

        # Each should be 32 characters (16 bytes hex-encoded)
        for challenge in challenges:
            assert len(challenge) == 32
            assert all(c in "0123456789abcdef" for c in challenge)

    def test_tcp_response_requires_password_knowledge(self):
        """Verify TCP response cannot be forged without password"""
        auth_server = Authenticator("correct_password")
        auth_attacker = Authenticator("wrong_password")

        challenge = auth_server.generate_tcp_challenge()

        # Attacker's response should fail
        attacker_response = auth_attacker.generate_tcp_response(challenge)
        assert auth_server.verify_tcp_response(challenge, attacker_response) is False

    def test_authentication_without_password(self):
        """Verify behavior when no password is set"""
        auth = Authenticator(None)

        # TCP authentication is optional when no password is configured.
        assert auth.verify_tcp_response("challenge", "any_response") is True


class TestRateLimitingSecurity:
    """Test rate limiting and DoS protection"""

    def test_rate_limiting_blocks_excessive_requests(self):
        """Verify rate limiting blocks clients exceeding limits"""
        tracker = ConnectionTracker(
            max_connections=1,
            rate_limit_window=10,  # 10 second window
            max_requests=5,  # Only 5 requests
            block_duration=2,  # Block for 2 seconds
        )

        client_addr = ("192.168.1.100", 12345)

        # First 5 requests should be allowed
        for _i in range(5):
            assert tracker.is_rate_limited(client_addr) is False

        # 6th request should be rate limited
        assert tracker.is_rate_limited(client_addr) is True

    def test_blocked_clients_tracked(self):
        """Verify blocked clients are properly tracked"""
        tracker = ConnectionTracker(
            max_connections=1, rate_limit_window=10, max_requests=3, block_duration=2
        )

        client_addr = ("192.168.1.100", 12345)

        # Trigger rate limit
        for _i in range(4):
            tracker.is_rate_limited(client_addr)

        # Client should be blocked
        assert tracker.is_blocked(client_addr) is True

    def test_connection_limit_enforcement(self):
        """Verify maximum connection limit is enforced"""
        tracker = ConnectionTracker(max_connections=1)

        client1 = ("192.168.1.100", 12345)
        client2 = ("192.168.1.101", 12346)

        # First client connects
        assert tracker.can_connect(client1) is True
        tracker.authenticate(client1)

        # Second client should be rejected (limit = 1)
        assert tracker.can_connect(client2) is False

    def test_per_client_rate_limiting(self):
        """Verify rate limiting is per-client, not global"""
        tracker = ConnectionTracker(
            max_connections=2, rate_limit_window=10, max_requests=3, block_duration=2
        )

        client1 = ("192.168.1.100", 12345)
        client2 = ("192.168.1.101", 12346)

        # Client1 makes requests
        for _i in range(3):
            tracker.is_rate_limited(client1)

        # Client2 should not be affected by client1's rate limit
        assert tracker.is_rate_limited(client2) is False


class TestInputValidationSecurity:
    """Mutate complete canonical snapshots so each rejection tests its own boundary."""

    def test_input_validation_rejects_invalid_type(self):
        from padrelay.core.controller_state import InputState

        packet = InputState().to_message()
        packet["type"] = "heartbeat"
        assert not validate_input_message(packet)

    @pytest.mark.parametrize("value", ["not-a-map", [True, False], None, False])
    def test_input_validation_rejects_invalid_buttons(self, value):
        from padrelay.core.controller_state import InputState

        packet = InputState().to_message()
        packet["buttons"] = value
        assert not validate_input_message(packet)

    @pytest.mark.parametrize("value", [-2.0, 1.5, float("nan"), float("inf"), True])
    def test_input_validation_rejects_out_of_range_axes(self, value):
        from padrelay.core.controller_state import InputState

        packet = InputState().to_message()
        packet["axes"]["left_x"] = value
        assert not validate_input_message(packet)

    @pytest.mark.parametrize("value", [-0.1, 1.5, float("nan"), False])
    def test_input_validation_rejects_invalid_triggers(self, value):
        from padrelay.core.controller_state import InputState

        packet = InputState().to_message()
        packet["triggers"]["left"] = value
        assert not validate_input_message(packet)

    def test_input_validation_rejects_physical_hats(self):
        from padrelay.core.controller_state import InputState

        packet = InputState().to_message()
        packet["hats"] = [[0, 1]]
        assert not validate_input_message(packet)

    def test_input_validation_accepts_valid_message(self):
        from padrelay.core.controller_state import InputState

        assert validate_input_message(
            InputState(
                frozenset({"a", "dpad_up"}), left_x=0.5, trigger_left=0.8
            ).to_message()
        )


class TestProtocolVersionSecurity:
    """Test protocol version handling to prevent downgrade attacks"""

    def test_protocol_version_constant_defined(self):
        """Verify protocol version is defined"""
        from padrelay.protocol.constants import PROTOCOL_VERSION

        assert PROTOCOL_VERSION == "2.0"

    def test_message_includes_protocol_version(self):
        """Verify all messages include protocol version"""
        from padrelay.protocol.messages import HeartbeatMessage, InputMessage

        msg = InputMessage()
        assert "protocol_version" in msg.data
        assert msg.data["protocol_version"] == "2.0"

        hb = HeartbeatMessage()
        assert "protocol_version" in hb.data


class TestSecretLeakagePrevention:
    """Test that secrets are not logged or exposed"""

    def test_password_not_in_hash_string(self):
        """Verify plaintext password is not in hash string"""
        password = "super_secret_password_12345"
        auth = Authenticator(password)
        hash_string = auth.get_hash_string()

        # Password should not appear in hash string
        assert password not in hash_string
        assert password.lower() not in hash_string.lower()

    def test_hash_uses_salt(self):
        """Verify hashes use salt (not just password hash)"""
        auth = Authenticator("test_password")

        # Salt should be present and non-empty
        assert auth.salt is not None
        assert len(auth.salt) == 32  # 16 bytes in hex

        # Hash should be present
        assert auth.password_hash is not None
        assert len(auth.password_hash) == 64  # SHA256 in hex


class TestCryptographicPrimitives:
    """Test underlying cryptographic operations"""

    def test_hmac_uses_sha256(self):
        """Verify HMAC operations use SHA256"""
        auth = Authenticator("test_password")
        challenge = "test_challenge"
        response = auth.generate_tcp_response(challenge)

        # SHA256 HMAC should produce 64 hex characters
        assert len(response) == 64
        assert all(c in "0123456789abcdef" for c in response)

    def test_pbkdf2_uses_sha256(self):
        """Verify PBKDF2 uses SHA256 as PRF"""
        auth = Authenticator("test_password")
        hash_string = auth.get_hash_string()

        # Should contain "pbkdf2_sha256" prefix
        assert hash_string.startswith("pbkdf2_sha256$")

    def test_secure_random_generation(self):
        """Verify secure random generation for salts"""
        auth1 = Authenticator("password1")
        auth2 = Authenticator("password2")

        # Salts should be different (cryptographically random)
        assert auth1.salt != auth2.salt

        # Generate multiple challenges
        challenges = [auth1.generate_tcp_challenge() for _ in range(50)]

        # All should be unique
        assert len(set(challenges)) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
