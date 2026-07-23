from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from config import settings


# Robust hashing with Argon2
password_hash = PasswordHash((Argon2Hasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password based on plain and hashed password

    Args:
        plain_password (str): password in plain format
        hashed_password (str): password in hashed format

    Returns:
        bool: True if valid, else False
    """

    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash the password

    Args:
        password (str): password to hash

    Returns:
        str: hashed password
    """

    return password_hash.hash(password)


def create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str = "access",
) -> str:
    """
    Create the token, based on given `subject`, `expires_delta` and `token_type`.

    Args:
        subject (str): the subject of the token
        expires_delta (timedelta): time delta to consider the token expired
        token_type (str): the token type, by default "access"

    Returns:
        str: the encoded token
    """

    now = datetime.now(timezone.utc)

    expire = now + expires_delta
    payload = {"sub": str(subject), "exp": expire, "iat": now, "type": token_type}

    return jwt.encode(
        payload,
        settings.auth.SECRET_KEY,
        algorithm=settings.auth.ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode a token

    Args:
        token (str): token to decode

    Return:
        dict[str, Any] | None: return the payload decoded or None if failed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.SECRET_KEY,
            algorithms=[settings.auth.ALGORITHM],
        )
        return payload
    except jwt.PyJWTError:
        return None
