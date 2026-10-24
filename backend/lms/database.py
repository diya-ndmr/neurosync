import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import DeclarativeBase, sessionmaker  # pyright: ignore[reportMissingImports]

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LMS_DB_PATH = ROOT_DIR / "database" / "mock_lms.db"
from app.config.settings import settings

CONFIGURED_LMS_DATABASE_URL = os.getenv("MOCK_LMS_DATABASE_URL")
if CONFIGURED_LMS_DATABASE_URL is None and settings.mock_lms_database_url != "sqlite:///./database/mock_lms.db":
    CONFIGURED_LMS_DATABASE_URL = settings.mock_lms_database_url


class LMSBase(DeclarativeBase):
    pass


def get_lms_database_url(db_path: Optional[str] = None, database_url: Optional[str] = None) -> str:
    if db_path:
        resolved = str(Path(db_path).expanduser().resolve())
        return f"sqlite:///{resolved}"
    if database_url:
        return database_url
    if CONFIGURED_LMS_DATABASE_URL:
        if CONFIGURED_LMS_DATABASE_URL.startswith("postgres://"):
            return CONFIGURED_LMS_DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return CONFIGURED_LMS_DATABASE_URL
    return f"sqlite:///{DEFAULT_LMS_DB_PATH}"


def build_lms_session_factory(db_path: Optional[str] = None, database_url: Optional[str] = None):
    url = get_lms_database_url(db_path, database_url)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        echo=False,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, session_factory


lms_engine, LMSSessionLocal = build_lms_session_factory(database_url=CONFIGURED_LMS_DATABASE_URL)


def ensure_lms_db(db_path: Optional[str] = None) -> str:
    target = Path(db_path).expanduser().resolve() if db_path else DEFAULT_LMS_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)


def get_lms_db(db_path: Optional[str] = None):
    _, session_factory = build_lms_session_factory(db_path)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
