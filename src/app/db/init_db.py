from app.db import engine
from app.db.base import Base
from app.models import (
    registration_requests,
    user_profile,
    users,
)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
