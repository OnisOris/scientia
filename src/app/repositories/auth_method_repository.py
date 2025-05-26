from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_methods import AuthMethod

from .base import GenericRepository


class AuthMethodRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuthMethod)

    async def get_by_type_and_user_id(
        self, auth_type: str, user_id: int
    ) -> AuthMethod | None:
        result = await self.session.execute(
            select(AuthMethod).where(
                AuthMethod.auth_type == auth_type,
                AuthMethod.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
