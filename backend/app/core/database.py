from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


pool_options = (
    {"pool_size": 1, "max_overflow": 0}
    if settings.sqlalchemy_database_url.startswith("postgresql+")
    else {}
)
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    **pool_options,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
