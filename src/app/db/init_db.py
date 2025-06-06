from app.db import engine
from app.db.base import Base


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
