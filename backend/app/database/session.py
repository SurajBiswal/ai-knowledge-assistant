"""Create SQLAlchemy database connections and request-scoped sessions.

Repositories receive a Session produced by ``get_db``. Successful FastAPI
requests are committed, failed requests are rolled back, and every session is
closed so database connections return to the pool.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

# The engine owns the connection pool. echo=True prints SQL for development.
engine = create_engine(
    DATABASE_URL,
    echo=True,
)

# SessionLocal creates independent units of database work for API requests.
# Explicit commit/rollback keeps transaction boundaries predictable.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# FastAPI calls this generator once per request that needs database access.
def get_db():
    """Yield one session, commit success, roll back failure, and always close."""
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        
# def get_db():
#     db = SessionLocal()

#     try:
#         yield db
#     finally:
#         db.close()
