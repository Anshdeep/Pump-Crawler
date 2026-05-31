import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Fallback database URL matches docker-compose services
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:postgres_password@localhost:5432/compressors_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dynamic vector support flag (checked at runtime / startup)
HAS_VECTOR_SUPPORT = False

try:
    with engine.connect() as _conn:
        _res = _conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"))
        HAS_VECTOR_SUPPORT = _res.scalar()
except Exception:
    HAS_VECTOR_SUPPORT = False


def init_db():
    """Create pgvector extension and create all tables if they don't exist."""
    global HAS_VECTOR_SUPPORT
    from database.models import Base
    
    # 1. Try to enable pgvector extension
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        HAS_VECTOR_SUPPORT = True
        print("[OK] PostgreSQL pgvector extension is enabled!")
    except Exception as e:
        HAS_VECTOR_SUPPORT = False
        print("\n" + "="*80)
        print("[WARNING] The pgvector extension is not installed or available in PostgreSQL.")
        print("  -> The system will automatically fall back to pure-Python cosine similarity search.")
        print("  -> You do not need to compile pgvector now! The system is fully operational using safe fallbacks.")
        print("="*80 + "\n")

    # 2. Create tables
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
    print("[DB] Database and tables initialized successfully!")


def get_db():
    """FastAPI dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
