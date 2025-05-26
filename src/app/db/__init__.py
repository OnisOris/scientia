from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

DB_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_async_engine(DB_URL, echo=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
