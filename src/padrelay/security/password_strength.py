"""Password strength checking utilities"""
import re
from typing import Tuple, List
from ..core.logging_utils import get_logger

logger = get_logger(__name__)


def check_password_strength(password: str) -> Tuple[str, int, List[str]]:
    """Check password strength and provide recommendations

    Args:
        password: The password to check

    Returns:
        Tuple of (strength_level, score, recommendations)
        - strength_level: "very_weak", "weak", "medium", "strong", "very_strong"
        - score: Integer score from 0-100
        - recommendations: List of improvement suggestions
    """
    if not password:
        return "very_weak", 0, ["Password is required"]

    score = 0
    recommendations = []

    # Length check
    length = len(password)
    if length < 8:
        recommendations.append("Use at least 8 characters (12+ recommended)")
    elif length < 12:
        score += 20
        recommendations.append("Consider using 12+ characters for better security")
    elif length < 16:
        score += 30
    else:
        score += 40

    # Character variety checks
    has_lowercase = bool(re.search(r'[a-z]', password))
    has_uppercase = bool(re.search(r'[A-Z]', password))
    has_digits = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password))

    char_types = sum([has_lowercase, has_uppercase, has_digits, has_special])

    if char_types == 1:
        score += 10
        recommendations.append("Mix uppercase and lowercase letters")
        recommendations.append("Add numbers and special characters")
    elif char_types == 2:
        score += 20
        if not has_digits:
            recommendations.append("Add numbers for better security")
        if not has_special:
            recommendations.append("Add special characters (!@#$%^&*, etc.)")
    elif char_types == 3:
        score += 30
        if not has_special:
            recommendations.append("Consider adding special characters for maximum security")
    else:  # char_types == 4
        score += 40

    # Common pattern checks
    common_patterns = [
        (r'123', "Avoid sequential numbers (123, 456, etc.)"),
        (r'abc', "Avoid sequential letters (abc, def, etc.)"),
        (r'qwerty', "Avoid keyboard patterns (qwerty, asdf, etc.)"),
        (r'password', "Don't use the word 'password'"),
        (r'admin', "Don't use the word 'admin'"),
        (r'(.)\1{2,}', "Avoid repeating characters (aaa, 111, etc.)"),
    ]

    for pattern, message in common_patterns:
        if re.search(pattern, password.lower()):
            score -= 10
            if message not in recommendations:
                recommendations.append(message)

    # Common weak passwords
    weak_passwords = [
        '123456', 'password', '12345678', 'qwerty', '123456789', '12345',
        '1234', '111111', '1234567', 'dragon', '123123', 'baseball',
        'abc123', 'football', 'monkey', 'letmein', 'shadow', 'master',
        'abc', '123', 'admin', 'test', 'guest'
    ]

    if password.lower() in weak_passwords:
        score = max(0, score - 30)
        recommendations.append("This is a commonly used password - choose something unique")

    # Ensure score is in 0-100 range
    score = max(0, min(100, score))

    # Determine strength level
    if score < 20:
        strength = "very_weak"
    elif score < 40:
        strength = "weak"
    elif score < 60:
        strength = "medium"
    elif score < 80:
        strength = "strong"
    else:
        strength = "very_strong"

    return strength, score, recommendations


def warn_weak_password(password: str) -> bool:
    """Check password strength and warn if weak

    Args:
        password: The password to check

    Returns:
        True if password is acceptable, False if very weak
    """
    # Skip check for hashed passwords
    if password and password.startswith('pbkdf2_sha256$'):
        return True

    strength, score, recommendations = check_password_strength(password)

    if strength == "very_weak":
        logger.error("=" * 70)
        logger.error("CRITICAL: Password is VERY WEAK!")
        logger.error(f"Password strength score: {score}/100")
        logger.error("")
        logger.error("Your password provides minimal security and can be easily guessed.")
        logger.error("Strongly consider using a stronger password.")
        logger.error("")
        if recommendations:
            logger.error("Recommendations:")
            for rec in recommendations:
                logger.error(f"  - {rec}")
        logger.error("=" * 70)
        return False

    elif strength == "weak":
        logger.warning("=" * 70)
        logger.warning("WARNING: Password is WEAK")
        logger.warning(f"Password strength score: {score}/100")
        logger.warning("")
        logger.warning("Your password provides limited security.")
        logger.warning("Consider using a stronger password for better protection.")
        logger.warning("")
        if recommendations:
            logger.warning("Recommendations:")
            for rec in recommendations:
                logger.warning(f"  - {rec}")
        logger.warning("=" * 70)
        return True

    elif strength == "medium":
        logger.info(f"Password strength: Medium (score: {score}/100)")
        if recommendations:
            logger.info("Suggestions to improve password strength:")
            for rec in recommendations:
                logger.info(f"  - {rec}")
        return True

    elif strength == "strong":
        logger.info(f"Password strength: Strong (score: {score}/100)")
        return True

    else:  # very_strong
        logger.info(f"Password strength: Very Strong (score: {score}/100)")
        return True


def generate_password_suggestion() -> str:
    """Generate a strong password suggestion

    Returns:
        A suggested strong password
    """
    import secrets
    import string

    # Use a mix of lowercase, uppercase, digits, and special chars
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    # Generate 16 character password
    password = ''.join(secrets.choice(chars) for _ in range(16))

    return password
