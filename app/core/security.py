from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import cache

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only looks at the first 72 bytes and bcrypt>=5 raises beyond that,
# so longer passwords are rejected up front instead of surfacing as a 500.
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    encoded = plain_password.encode()
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes long")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded = plain_password.encode()
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(encoded, hashed_password.encode())


@cache
def _dummy_hash() -> str:
    return hash_password("dummy-password-for-timing")


def burn_password_check(plain_password: str) -> None:
    """Spends the same time as a real password check. Called when the login
    document doesn't match an active user, so response time doesn't reveal
    which documents exist."""
    verify_password(plain_password, _dummy_hash())


def derive_initial_password(document: str) -> str:
    """Initial password derived from the document number (RNG-06, RN-09)."""
    return document[-4:]


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    version: int


def create_access_token(subject: str, token_version: int = 0) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "ver": token_version, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenClaims | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    return TokenClaims(subject=subject, version=payload.get("ver", 0))
