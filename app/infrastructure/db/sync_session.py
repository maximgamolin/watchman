from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.infrastructure.config import settings

sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_session() -> Session:
    return SyncSessionLocal()
