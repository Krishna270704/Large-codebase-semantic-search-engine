"""
utils.py — Sample utility functions for testing the search engine.

Contains logging setup, configuration loading, rate limiting,
and data validation helpers.
"""

import logging
import os
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict, Optional


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(
    level: str = "INFO",
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure application-wide logging.

    Parameters
    ----------
    level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_format : str
        Format string for log messages.
    log_file : str, optional
        If provided, logs are also written to this file.

    Returns
    -------
    logging.Logger
        The root logger instance.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    logger = logging.getLogger("app")
    logger.info(f"Logging initialized at level {level}")
    return logger


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------

class Config:
    """Application configuration loaded from environment variables.

    Falls back to sensible defaults when variables are not set.
    """

    def __init__(self):
        self.debug = os.environ.get("APP_DEBUG", "false").lower() == "true"
        self.port = int(os.environ.get("APP_PORT", "8000"))
        self.host = os.environ.get("APP_HOST", "0.0.0.0")
        self.db_path = os.environ.get("APP_DB_PATH", "app.sqlite3")
        self.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.max_request_size = int(os.environ.get("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))

    def __repr__(self) -> str:
        return (
            f"Config(debug={self.debug}, host={self.host}, port={self.port}, "
            f"db_path={self.db_path}, log_level={self.log_level})"
        )


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple in-memory rate limiter using a sliding window.

    Parameters
    ----------
    max_requests : int
        Maximum number of requests allowed per window.
    window_seconds : int
        Duration of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check whether a client is within their rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        # Purge old entries
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > window_start
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        """Return how many requests the client has left in the current window."""
        now = time.time()
        window_start = now - self.window_seconds
        recent = [ts for ts in self._requests[client_id] if ts > window_start]
        return max(0, self.max_requests - len(recent))


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_email(email: str) -> str:
    """Validate and normalize an email address.

    Returns the normalized email, or raises ``ValidationError``.
    """
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email address: {email}")
    return email


def validate_username(username: str) -> str:
    """Validate a username (3–30 alphanumeric + underscore characters)."""
    username = username.strip()
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
        raise ValidationError(
            "Username must be 3–30 characters, using only letters, numbers, and underscores"
        )
    return username


def validate_password(password: str) -> str:
    """Validate password strength."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one digit")
    return password


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator that retries a function on exception.

    Parameters
    ----------
    max_attempts : int
        Maximum number of attempts.
    delay : float
        Initial delay between retries (seconds).
    backoff : float
        Multiplier applied to delay after each retry.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        raise
                    logging.warning(
                        f"Attempt {attempt}/{max_attempts} for {func.__name__} failed: {exc}. "
                        f"Retrying in {current_delay:.1f}s …"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
