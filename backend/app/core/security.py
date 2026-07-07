from passlib.context import CryptContext

from datetime import datetime, timezone
from datetime import timedelta

from jose import jwt
from jose import JWTError

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(
    password: str,
) -> str:

    return pwd_context.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    user_id: str,
) -> str:

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