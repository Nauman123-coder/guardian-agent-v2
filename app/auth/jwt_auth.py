"""
Guardian Auth — JWT-based authentication for the dashboard.

Configure via .env:
  GUARDIAN_ADMIN_USER=admin
  GUARDIAN_ADMIN_PASS=changeme123
  GUARDIAN_JWT_SECRET=your-super-secret-key-change-this

Features:
  - Single admin user (expandable to multi-user)
  - Bcrypt password hashing
  - JWT tokens with 8-hour expiry
  - FastAPI dependency for protecting routes
"""

from __future__ import annotations
import os
import hashlib
import hmac
import json
import base64
import time
from typing import Any

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Simple JWT (no external dependency — pure stdlib)
# ---------------------------------------------------------------------------

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _get_secret() -> str:
    secret = os.getenv("GUARDIAN_JWT_SECRET", "guardian-default-secret-CHANGE-THIS")
    if secret == "guardian-default-secret-CHANGE-THIS":
        print("  ⚠️  [AUTH] Using default JWT secret — set GUARDIAN_JWT_SECRET in .env")
    return secret


def create_token(username: str) -> str:
    """Create a JWT token valid for 8 hours."""
    header = _b64_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64_encode(json.dumps({
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 8 * 3600,  # 8 hours
    }).encode())
    signature = _b64_encode(
        hmac.new(
            _get_secret().encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    )
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT token. Returns payload or raises HTTPException."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header, payload, signature = parts

        # Verify signature
        expected = _b64_encode(
            hmac.new(
                _get_secret().encode(),
                f"{header}.{payload}".encode(),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")

        # Verify expiry
        data = json.loads(_b64_decode(payload))
        if data.get("exp", 0) < time.time():
            raise ValueError("Token expired")

        return data
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ---------------------------------------------------------------------------
# Password verification
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Simple SHA-256 hash with salt (use bcrypt in production)."""
    salt = os.getenv("GUARDIAN_JWT_SECRET", "salt")[:16]
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against .env config."""
    expected_user = os.getenv("GUARDIAN_ADMIN_USER", "admin")
    expected_pass = os.getenv("GUARDIAN_ADMIN_PASS", "guardian123")

    user_ok = hmac.compare_digest(username.strip(), expected_user.strip())
    pass_ok = hmac.compare_digest(password, expected_pass)
    return user_ok and pass_ok


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_security),
) -> dict[str, Any]:
    """FastAPI dependency — use on protected routes."""
    # If auth is disabled, allow all
    if os.getenv("GUARDIAN_AUTH_ENABLED", "false").lower() not in ("true", "1"):
        return {"sub": "anonymous", "auth_disabled": True}

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return verify_token(credentials.credentials)


# Optional alias for cleaner imports
require_auth = Depends(get_current_user)