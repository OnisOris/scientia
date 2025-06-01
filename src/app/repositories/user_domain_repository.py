import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_domains import UserDomain

from .base import GenericRepository


class UserDomainRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserDomain)

    async def get_by_user(self, user_id: uuid.UUID):
        result = await self.session.execute(
            select(UserDomain).where(UserDomain.user_id == user_id)
        )
        return result.scalars().all()
