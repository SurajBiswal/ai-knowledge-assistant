from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

# Database setup and session management

# Create the SQLAlchemy engine using the DATABASE_URL from the configuration file. The echo=True parameter enables logging of all SQL statements, which is useful for debugging.
engine = create_engine(
    DATABASE_URL,
    echo=True,
)

# Create a configured "SessionLocal" class using sessionmaker. 
# This class will be used to create new database sessions. 
# The autocommit=False parameter means that changes to the database will not be automatically committed, and autoflush=False means that changes will not be automatically flushed to the database before queries.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Dependency function to get a database session. 
# This function can be used in FastAPI routes to provide a database session for each request. 
# It ensures that the session is properly closed after the request is completed, even if an error occurs.
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()