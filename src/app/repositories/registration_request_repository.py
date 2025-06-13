from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.registration_requests import RegistrationRequest

from .base import GenericRepository

# Нужно для запроса на регистрацию пользователей (подтверждается админами)


class RegistrationRequestRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, RegistrationRequest)

    async def get_by_telegram_id(self, telegram_id: int):
        result = await self.session.execute(
            select(self.model).where(self.model.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
