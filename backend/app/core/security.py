"""Password hashing and short lived JWT access tokens."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.settings import Settings


ALGORITHM = "HS256"
ISSUER = "gridwatch"
AUDIENCE = "gridwatch-api"
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("gridwatch-timing-placeholder")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_ttl_minutes),
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise ValueError("Invalid access token") from exc
