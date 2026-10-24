"""Password hashing and JWT issuance.

Password hashes are produced with the ``bcrypt`` library directly. passlib 1.7.4
(unmaintained since 2020) cannot initialise a bcrypt >= 4.1 backend: its wrap-bug
probe hashes a secret longer than 72 bytes and newer bcrypt releases raise instead
of truncating, which made every /api/auth/login call fail with HTTP 500.
Existing ``$2b$`` hashes created through passlib are standard bcrypt hashes and keep
verifying unchanged.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import jwt

from app.config.settings import settings

# bcrypt only consumes the first 72 bytes of a password; longer input is truncated
# (the same behaviour passlib used) so hashing never raises on long passphrases.
BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed or unsupported stored hash is a failed login, never a 500.
        return False


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    to_encode: dict[str, Any] = {"sub": user_id}
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
