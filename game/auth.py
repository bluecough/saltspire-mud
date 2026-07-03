"""Password hashing for the local character database.

Stdlib-only (no bcrypt/passlib dependency): salted PBKDF2-HMAC-SHA256 with a
high iteration count. This is reasonable for a small self-hosted prototype
with a local JSON "user database," but it is not a substitute for a vetted
auth system if this ever needs to face the wider internet.
"""
from __future__ import annotations
import hashlib
import hmac
import secrets

_ITERATIONS = 200_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Returns (hash_hex, salt_hex). Generates a new random salt if none given."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    )
    return digest.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    if not salt or not expected_hash:
        return False
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def is_valid_password(password: str) -> bool:
    return bool(password) and 4 <= len(password) <= 64
