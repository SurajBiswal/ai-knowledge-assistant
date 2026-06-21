from sqlalchemy.orm import DeclarativeBase

# Base class for SQLAlchemy models

# The Base class is a subclass of DeclarativeBase, which is used to define the base class for all SQLAlchemy models in the application.
class Base(DeclarativeBase):
    pass

import app.models