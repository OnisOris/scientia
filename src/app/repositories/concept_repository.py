from sqlalchemy.ext.asyncio import AsyncSession
from app.models.concepts import Concept
from .base import GenericRepository


class ConceptRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Concept)

    async def get_or_create(
        self, name: str, domain_id: int, description: str = None
    ):
        concept = await self.get_first(name=name)
        if concept:
            return concept

        return await self.add(
            Concept(
                name=name,
                domain_id=domain_id,
                description=description or "Автоматически извлеченный термин",
            )
        )
