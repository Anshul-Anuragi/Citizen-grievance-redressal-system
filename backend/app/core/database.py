import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.core.config import settings

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "asyncpg" in url:
        parsed = urlparse(url)
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            query_params.pop("channel_binding", None)
            if "sslmode" in query_params:
                sslmode_val = query_params.pop("sslmode")[0]
                query_params["ssl"] = [sslmode_val]
            flattened = [(k, v[0] if len(v) == 1 else v) for k, v in query_params.items()]
            new_query = urlencode(flattened, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))
    return url

database_url = normalize_database_url(settings.DATABASE_URL)

# Configure Engine
connect_args = {}
if "sqlite" in database_url:
    connect_args["check_same_thread"] = False
elif "asyncpg" in database_url:
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    connect_args=connect_args
)

# Enable Foreign Keys in SQLite
if "sqlite" in database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
