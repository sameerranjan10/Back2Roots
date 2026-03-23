import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
load_dotenv()
# ─── Connection URL ────────────────────────────────────────────────────────────
# Override via environment variable in production:
#   export DATABASE_URL="mysql+pymysql://user:pass@host:3306/alumni_db"
DATABASE_URL = os.environ.get("DATABASE_URL")

# ─── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # reconnect on stale connections
    pool_recycle=3600,        # recycle connections every hour
    pool_size=10,
    max_overflow=20,
    echo=False,               # set True to log all SQL to stdout
)

# ─── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ─── Base class for ORM models ─────────────────────────────────────────────────
Base = declarative_base()


# ─── Dependency ────────────────────────────────────────────────────────────────
def get_db():
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
