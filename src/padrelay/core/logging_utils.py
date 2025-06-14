"""Logging utilities"""

import logging
import logging.handlers
import os
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

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
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
