"""Database setup for the prediction market backend.

This module configures a SQLAlchemy engine and session factory. It reads the
``DATABASE_URL`` environment variable to determine how to connect to the
database. If no environment variable is set, it falls back to an in‑process
SQLite database, which is convenient for local development and testing.

The ``get_db`` function is provided as a FastAPI dependency to obtain a
database session for each request. Sessions are automatically closed after
the request lifecycle.
"""

# to recommit

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Read the database URL from the environment. For production use a PostgreSQL
# URI in the form ``postgresql+psycopg2://user:password@host:port/dbname``.
# When developing locally without a running Postgres instance, the fallback
# SQLite URI is used instead. You can override this by setting the
# ``DATABASE_URL`` environment variable before starting the application.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/prediction_market.db")

# Configure the SQLAlchemy engine. SQLite requires special options for
# multi‑threaded access. Other backends such as PostgreSQL do not need
# additional arguments.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

# A session factory bound to our engine. The ``autocommit`` and ``autoflush``
# options are disabled to give us explicit control over when commits happen.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models.
Base = declarative_base()


def get_db():
    """Yield a database session for a single request.

    This function is designed to be used as a FastAPI dependency. It creates
    a new SQLAlchemy session from ``SessionLocal`` and yields it. After the
    request is finished, the session is closed automatically.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()