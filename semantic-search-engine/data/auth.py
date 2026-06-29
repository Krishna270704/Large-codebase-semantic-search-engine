"""
auth.py — Sample authentication module for testing the search engine.

Provides JWT-based authentication with login, token validation,
and role-based access control.
"""

import hashlib
import hmac
import json
import time
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = "super-secret-key-change-in-production"
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour


# ---------------------------------------------------------------------------
# User store (in-memory for demo)
# ---------------------------------------------------------------------------

_USERS_DB: dict[str, dict] = {
    "admin": {
        "password_hash": hashlib.sha256(b"admin123").hexdigest(),
        "role": "admin",
        "email": "admin@example.com",
    },
    "user1": {
        "password_hash": hashlib.sha256(b"pass456").hexdigest(),
        "role": "viewer",
        "email": "user1@example.com",
    },
}


def _hash_password(password: str) -> str:
    """Hash a plaintext password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Authentication logic
# ---------------------------------------------------------------------------

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthManager:
    """Handles user authentication and JWT-like token management."""

    def __init__(self, secret_key: str = SECRET_KEY):
        self.secret_key = secret_key

    def login(self, username: str, password: str) -> str:
        """Authenticate a user and return a signed token.

        Parameters
        ----------
        username : str
            The user's login name.
        password : str
            The plaintext password.

        Returns
        -------
        str
            A signed authentication token.

        Raises
        ------
        AuthenticationError
            If the credentials are invalid.
        """
        user = _USERS_DB.get(username)
        if user is None:
            raise AuthenticationError(f"Unknown user: {username}")

        if _hash_password(password) != user["password_hash"]:
            raise AuthenticationError("Invalid password")

        payload = {
            "sub": username,
            "role": user["role"],
            "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        }
        return self._sign_token(payload)

    def validate_token(self, token: str) -> dict:
        """Validate a token and return its payload.

        Raises
        ------
        AuthenticationError
            If the token is invalid or expired.
        """
        payload = self._verify_token(token)

        if payload["exp"] < time.time():
            raise AuthenticationError("Token has expired")

        return payload

    def require_role(self, token: str, required_role: str) -> dict:
        """Validate a token and check that the user has the required role."""
        payload = self.validate_token(token)
        if payload.get("role") != required_role:
            raise AuthenticationError(
                f"Access denied: requires role '{required_role}', "
                f"but user has role '{payload.get('role')}'"
            )
        return payload

    # ------------------------------------------------------------------
    # Token signing / verification (simplified JWT-like)
    # ------------------------------------------------------------------

    def _sign_token(self, payload: dict) -> str:
        """Create a signed token from a payload dict."""
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_json}|{signature}"

    def _verify_token(self, token: str) -> dict:
        """Verify token signature and return the payload."""
        try:
            payload_json, signature = token.rsplit("|", 1)
        except ValueError:
            raise AuthenticationError("Malformed token")

        expected_sig = hmac.new(
            self.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise AuthenticationError("Invalid token signature")

        return json.loads(payload_json)
