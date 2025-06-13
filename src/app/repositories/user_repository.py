from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User

from .base import GenericRepository


class UserRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    # async def get_by_email(self, email: str) -> User | None:
    #     result = await self.session.execute(
    #         select(User).where(User.email == email)
    #     )
    #     return result.scalar_one_or_none()
