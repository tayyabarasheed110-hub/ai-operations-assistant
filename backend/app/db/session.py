from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
engine = create_engine(_settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    get_settings().data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
