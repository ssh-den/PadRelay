"""Tests for log sanitization"""
import pytest
from padrelay.core.logging_utils import sanitize_for_logging


class TestLogSanitization:
    """Test log sanitization functionality"""

    def test_sanitize_normal_string(self):
        """Test that normal strings pass through unchanged"""
        text = "Normal log message"
        result = sanitize_for_logging(text)
        assert result == text

    def test_sanitize_newlines(self):
        """Test that newlines are escaped"""
        text = "Line 1\nLine 2\nLine 3"
        result = sanitize_for_logging(text)
        assert "\n" not in result
        assert "\\n" in result
        assert result == "Line 1\\nLine 2\\nLine 3"

    def test_sanitize_carriage_returns(self):
        """Test that carriage returns are escaped"""
        text = "Line 1\rLine 2"
        result = sanitize_for_logging(text)
        assert "\r" not in result
        assert "\\r" in result
        assert result == "Line 1\\rLine 2"

    def test_sanitize_mixed_newlines(self):
        """Test that mixed newlines and carriage returns are escaped"""
        text = "Line 1\r\nLine 2\nLine 3"
        result = sanitize_for_logging(text)
        assert result == "Line 1\\r\\nLine 2\\nLine 3"

    def test_sanitize_control_characters(self):
        """Test that control characters are removed"""
        # Include various control characters
        text = "Hello\x00World\x01Test\x1fEnd"
        result = sanitize_for_logging(text)
        # Control characters should be removed
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x1f" not in result
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_max_length(self):
        """Test that long strings are truncated"""
        text = "A" * 300
        result = sanitize_for_logging(text, max_length=200)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_sanitize_custom_max_length(self):
        """Test custom max length"""
        text = "A" * 150
        result = sanitize_for_logging(text, max_length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_sanitize_short_string_no_truncation(self):
        """Test that short strings are not truncated"""
        text = "Short string"
        result = sanitize_for_logging(text, max_length=200)
        assert result == text
        assert not result.endswith("...")

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string"""
        result = sanitize_for_logging("")
        assert result == ""

    def test_sanitize_non_string_input(self):
        """Test sanitizing non-string input"""
        result = sanitize_for_logging(12345)
        assert result == "12345"

        result = sanitize_for_logging(None)
        assert result == "None"

    def test_sanitize_unicode(self):
        """Test that unicode characters are preserved"""
        text = "Hello 世界 🌍"
        result = sanitize_for_logging(text)
        assert result == text

    def test_sanitize_injection_attempt(self):
        """Test potential log injection attempts"""
        # Simulate log injection attempt
        text = "User: admin\nFake log: [ERROR] Access granted"
        result = sanitize_for_logging(text)
        # Newlines should be escaped, preventing injection
        assert "\n" not in result
        assert "\\n" in result

    def test_sanitize_ansi_escape_codes(self):
        """Test ANSI escape codes are removed"""
        # ANSI escape code for red color
        text = "Normal text\x1b[31mRed text\x1b[0mNormal again"
        result = sanitize_for_logging(text)
        # Escape codes should be removed
        assert "\x1b" not in result

    def test_sanitize_tab_characters(self):
        """Test that tab characters are preserved"""
        text = "Column1\tColumn2\tColumn3"
        result = sanitize_for_logging(text)
        # Tabs are allowed and should be preserved
        assert "\t" in result
        assert result == text

    def test_sanitize_special_characters(self):
        """Test that normal special characters are preserved"""
        text = "Special: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = sanitize_for_logging(text)
        assert result == text

    def test_sanitize_ip_address(self):
        """Test IP address sanitization"""
        text = "192.168.1.1"
        result = sanitize_for_logging(text)
        assert result == text

    def test_sanitize_complex_injection(self):
        """Test complex log injection with multiple techniques"""
        text = "User: attacker\r\n[CRITICAL] System compromised\x00Hidden text\x1b[31m"
        result = sanitize_for_logging(text)
        # All control characters and newlines should be handled
        assert "\r" not in result
        assert "\n" not in result
        assert "\x00" not in result
        assert "\x1b" not in result
        assert "\\r\\n" in result
