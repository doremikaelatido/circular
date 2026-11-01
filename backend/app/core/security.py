from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> tuple[str, int]:
    expires_seconds = settings.jwt_access_token_minutes * 60
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(seconds=expires_seconds),
            "jti": str(uuid4()),
            "typ": "access",
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    return token, expires_seconds


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require_sub": True, "require_exp": True, "require_iat": True, "require_jti": True},
        )
    except JWTError as exc:
        raise ValueError("Invalid access token") from exc
    subject = payload.get("sub")
    issued_at = payload.get("iat")
    token_id = payload.get("jti")
    if (
        not isinstance(subject, str)
        or not subject.isdecimal()
        or payload.get("typ") != "access"
        or not isinstance(issued_at, (int, float))
        or issued_at > datetime.now(UTC).timestamp() + 60
        or not isinstance(token_id, str)
        or not token_id
    ):
        raise ValueError("Invalid access token subject")
    return payload
