"""Password hashing and JWT access-token helpers.

AuthService uses these functions during registration and login. The FastAPI
``get_current_user`` dependency uses ``verify_token`` on protected requests.
Plain passwords are never stored in the database.
"""

from passlib.context import CryptContext

from datetime import datetime, timezone
from datetime import timedelta

from jose import jwt
from jose import JWTError

from app.core.config import settings

# Shared password hasher that can verify existing bcrypt formats.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(
    password: str,
) -> str:
    """Turn a plain password into the irreversible value stored for a user."""

    return pwd_context.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Return whether a login password matches the stored password hash."""

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    user_id: str,
) -> str:
    """Create a signed JWT containing the user ID and expiration time."""

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token


def verify_token(
    token: str,
) -> str:
    """Validate a JWT and return its user ID, or raise for an invalid token."""

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[
                settings.JWT_ALGORITHM
            ],
        )

        user_id = payload.get(
            "sub"
        )

        if not user_id:
            raise ValueError(
                "Invalid token"
            )

        return user_id

    except JWTError:
        raise ValueError(
            "Invalid token"
        )
