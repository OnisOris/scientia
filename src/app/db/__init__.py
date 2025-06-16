from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.settings import settings

# DB_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
engine = create_async_engine(settings.DATABASE_URL, echo=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
