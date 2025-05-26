from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domains import Domain

from .base import GenericRepository


class DomainRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Domain)

    async def add(self, entity):
        try:
            existing = await self.get_first(name=entity.name)
            if existing:
                return existing
            return await super().add(entity)
        except IntegrityError as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Domain '{entity.name}' already exists",
            ) from e
