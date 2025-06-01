from app.db import engine
from app.db.base import Base

from app.models import (
    users,
    user_profile,
    auth_methods,
    domains,
    user_domains,
    concepts,
    user_knowledge,
    retention_log,
    registration_requests,
)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
