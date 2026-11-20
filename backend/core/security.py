"""
SentinelOps AI - Security Utilities.
Provides password hashing (bcrypt), JWT generation/validation (PyJWT),
and secure collector token generation & hashing (SHA-256).
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "sentinelops-jwt-default-development-secret-key-32chars")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


def hash_password(password: str) -> str:
    """
    Securely hash a plaintext password using bcrypt with salt.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a signed JWT access token with an expiration claim.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a signed JWT token.
    Raises jwt.PyJWTError if expired, tampered, or invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def generate_collector_token() -> str:
    """
    Generate an unguessable high-entropy collector enrollment/auth token.
    Shown only once to the administrator upon creation.
    """
    return f"sc_live_{secrets.token_urlsafe(32)}"


def hash_collector_token(raw_token: str) -> str:
    """
    Compute deterministic SHA-256 hash of a collector token for safe database persistence.
    Raw tokens are never stored in the database.
    """
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
