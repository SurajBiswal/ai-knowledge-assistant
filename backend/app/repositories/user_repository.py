"""Database operations for User records.

AuthService uses this repository during registration and login. The JWT
dependency also uses it to load the current user from the token's user ID.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

class UserRepository:
    """Create and find users without exposing SQL queries to the service layer."""

    def __init__(
        self,
        db: Session,
    ):
        """Store the request's database session for user operations."""
        self.db = db


    def create(
    self,
    name: str,
    email: str,
    password_hash: str,
) -> User:
        """Create a user with an already-hashed password and return the record."""
        user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user
    

    def get_by_email(
    self,
    email: str,
) -> User | None:
        """Find the account that uses this email address, or return None."""
        stmt = (
            select(User)
            .where(User.email == email)
        )

        result = self.db.execute(stmt)

        return result.scalar_one_or_none()
    


    def get_by_id(
    self,
    user_id: UUID,
) -> User | None:
        """Find a user by UUID, as required by authenticated API requests."""
        stmt = (
            select(User)
            .where(User.id == user_id)
        )

        result = self.db.execute(stmt)

        return result.scalar_one_or_none()
