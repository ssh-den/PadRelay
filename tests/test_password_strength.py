"""Tests for password strength checking"""
import pytest
from padrelay.security.password_strength import (
    check_password_strength,
    warn_weak_password,
    generate_password_suggestion,
)


class TestPasswordStrengthCheck:
    """Test password strength checking functionality"""

    def test_empty_password(self):
        """Test that empty password is very weak"""
        strength, score, recommendations = check_password_strength("")
        assert strength == "very_weak"
        assert score == 0
        assert "Password is required" in recommendations

    def test_very_weak_password(self):
        """Test that common weak passwords are detected"""
        strength, score, recommendations = check_password_strength("123")
        assert strength == "very_weak"
        assert score < 20

    def test_weak_password(self):
        """Test weak password detection"""
        strength, score, recommendations = check_password_strength("password")
        assert strength in ["very_weak", "weak"]
        assert any("commonly used" in r.lower() for r in recommendations)

    def test_medium_password(self):
        """Test medium strength password"""
        strength, score, recommendations = check_password_strength("MyPass123")
        assert strength in ["weak", "medium"]
        assert score >= 20

    def test_strong_password(self):
        """Test strong password"""
        strength, score, recommendations = check_password_strength("MyStr0ng!Pass")
        assert strength in ["medium", "strong"]
        assert score >= 40

    def test_very_strong_password(self):
        """Test very strong password"""
        strength, score, recommendations = check_password_strength("MyV3ry$tr0ng!P@ssw0rd")
        assert strength in ["strong", "very_strong"]
        assert score >= 60

    def test_length_requirement(self):
        """Test that short passwords get recommendations"""
        _, _, recommendations = check_password_strength("Ab1!")
        assert any("8 characters" in r for r in recommendations)

    def test_character_variety_lowercase_only(self):
        """Test password with only lowercase letters"""
        strength, score, recommendations = check_password_strength("abcdefgh")
        assert any("uppercase" in r.lower() for r in recommendations)
        assert any("numbers" in r.lower() for r in recommendations)

    def test_character_variety_mixed(self):
        """Test password with mixed character types"""
        strength, score, recommendations = check_password_strength("Abc123!@#")
        # Should have good score with all character types
        assert score >= 40

    def test_sequential_numbers(self):
        """Test detection of sequential numbers"""
        strength, score, recommendations = check_password_strength("Pass123word")
        assert any("sequential" in r.lower() for r in recommendations)

    def test_repeated_characters(self):
        """Test detection of repeated characters"""
        strength, score, recommendations = check_password_strength("Passsss111!")
        assert any("repeating" in r.lower() for r in recommendations)

    def test_keyboard_pattern(self):
        """Test detection of keyboard patterns"""
        strength, score, recommendations = check_password_strength("qwerty123")
        assert any("keyboard" in r.lower() for r in recommendations)

    def test_common_words(self):
        """Test detection of common words"""
        for word in ["password", "admin"]:
            strength, score, recommendations = check_password_strength(word)
            assert strength in ["very_weak", "weak"]

    def test_score_range(self):
        """Test that score is always in valid range"""
        test_passwords = ["", "a", "abc", "Abc123", "MyStr0ng!P@ss", ""]
        for pwd in test_passwords:
            _, score, _ = check_password_strength(pwd)
            assert 0 <= score <= 100


class TestWarnWeakPassword:
    """Test password strength warning functionality"""

    def test_skip_hashed_password(self):
        """Test that hashed passwords are not checked"""
        result = warn_weak_password("pbkdf2_sha256$100000$salt$hash")
        assert result is True

    def test_very_weak_password_warning(self):
        """Test that very weak passwords return False"""
        result = warn_weak_password("123")
        assert result is False

    def test_weak_password_warning(self):
        """Test that weak passwords return True but warn"""
        result = warn_weak_password("password123")
        assert result is True

    def test_strong_password_no_warning(self):
        """Test that strong passwords return True"""
        result = warn_weak_password("MyStr0ng!P@ssw0rd")
        assert result is True

    def test_empty_password(self):
        """Test empty password handling"""
        result = warn_weak_password("")
        assert result is False


class TestGeneratePasswordSuggestion:
    """Test password suggestion generation"""

    def test_generated_password_length(self):
        """Test that generated password has correct length"""
        password = generate_password_suggestion()
        assert len(password) == 16

    def test_generated_password_strength(self):
        """Test that generated password is strong"""
        password = generate_password_suggestion()
        strength, score, _ = check_password_strength(password)
        # Generated password should be at least strong
        assert strength in ["strong", "very_strong"]
        assert score >= 60

    def test_generated_password_uniqueness(self):
        """Test that generated passwords are different"""
        passwords = [generate_password_suggestion() for _ in range(10)]
        # All passwords should be unique
        assert len(set(passwords)) == len(passwords)
