"""Logging utilities"""

import logging
import logging.handlers
import os
import re
from pathlib import Path



_LOG_FILE_NAME = "padrelay.log"


def _default_log_dir() -> Path:
    """Logging dir — ~/.padrelay/logs (override with PADRELAY_LOG_DIR)"""
    return Path(os.getenv("PADRELAY_LOG_DIR", Path.home() / ".padrelay" / "logs"))


_LOG_DIR = _default_log_dir()


def _setup_root_logger(log_dir: Path) -> None:
    """Configure file and console logging"""

    log_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(log_dir, 0o700)
    log_file = log_dir / _LOG_FILE_NAME

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    # Rotate logs to prevent uncontrolled growth
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Check for DEBUG environment variable
    debug_mode = os.getenv("PADRELAY_DEBUG", "").lower() in ("1", "true", "yes", "on")
    log_level = logging.DEBUG if debug_mode else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a :class:`logging.Logger` configured for the project"""

    if not logging.getLogger().handlers:
        log_dir_env = os.getenv("PADRELAY_LOG_DIR")
        log_dir = Path(log_dir_env) if log_dir_env else _LOG_DIR
        try:
            _setup_root_logger(log_dir)
        except Exception as exc:  # pragma: no cover - logging failure is non-critical
            logging.basicConfig(level=logging.INFO)
            logging.getLogger(__name__).error(
                "Failed to configure file logging: %s", exc
            )

    return logging.getLogger(name)


def sanitize_for_logging(value: str, max_length: int = 200) -> str:
    """Sanitize user input before logging to prevent log injection

    Args:
        value: The string to sanitize
        max_length: Maximum length of the output string

    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(value, str):
        value = str(value)

    # Replace newlines and carriage returns to prevent log injection
    sanitized = value.replace('\n', '\\n').replace('\r', '\\r')

    # Replace other control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)

    # Limit length to prevent log flooding
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + '...'

    return sanitized
