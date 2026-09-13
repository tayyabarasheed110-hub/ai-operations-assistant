from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
from app.models import (  # noqa: F401
    AuditLog,
    Document,
    DocumentChunk,
    EmailMessage,
    Order,
    Product,
    Thread,
    User,
    UserCapability,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _ensure_sqlite_parent_dir() -> None:
    """SQLite will not create missing parent folders for the db file."""
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    url = settings.database_url
    if url.startswith("sqlite"):
        # sqlite:///./data/app.db -> ./data/app.db
        path_part = url.split("sqlite:///")[-1].split("sqlite://")[-1]
        if path_part and path_part != ":memory:" and not path_part.startswith("/"):
            from pathlib import Path

            Path(path_part).parent.mkdir(parents=True, exist_ok=True)


def run_migrations_offline() -> None:
    _ensure_sqlite_parent_dir()
    url = get_settings().database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _ensure_sqlite_parent_dir()
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_settings().database_url
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
