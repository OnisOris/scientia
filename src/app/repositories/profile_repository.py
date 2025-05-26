from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile

from .base import GenericRepository


class ProfileRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserProfile)

    async def get_one(self, **kwargs):
        result = await self.session.execute(
            select(self.model).filter_by(**kwargs)
        )
        return result.scalars().first()
