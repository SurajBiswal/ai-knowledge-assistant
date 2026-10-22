"""Shared SQLAlchemy base class for all database models.

Every model inherits from ``Base``. Importing ``app.models`` at the end ensures
SQLAlchemy knows about all mapped tables when metadata or migrations are used.
"""

from sqlalchemy.orm import DeclarativeBase

# SQLAlchemy models inherit from this class to join the same metadata collection.
class Base(DeclarativeBase):
    """Provide shared SQLAlchemy metadata for every database model."""

    pass

# Register every model after Base exists, avoiding circular imports during setup.
import app.models
