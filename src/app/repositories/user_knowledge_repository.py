import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.concepts import Concept
from app.models.user_knowledge import UserKnowledge

from .base import GenericRepository


class UserKnowledgeRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserKnowledge)

    async def get_by_user_with_concepts(
        self, user_id: uuid.UUID, limit: int = 20, min_retention: float = 0.0
    ):
        """Возвращает знания пользователя с названиями концептов"""
        query = (
            select(UserKnowledge, Concept.name)
            .join(Concept, UserKnowledge.concept_id == Concept.id)
            .where(UserKnowledge.user_id == user_id)
            .where(UserKnowledge.retention >= min_retention)
            .order_by(UserKnowledge.next_review.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        min_retention: float = None,
        max_retention: float = None,
    ):
        query = select(UserKnowledge).where(UserKnowledge.user_id == user_id)

        if min_retention is not None:
            query = query.where(UserKnowledge.retention >= min_retention)

        if max_retention is not None:
            query = query.where(UserKnowledge.retention <= max_retention)

        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def avg_retention_by_user(self, user_id: uuid.UUID):
        result = await self.session.execute(
            select(func.avg(UserKnowledge.retention)).where(
                UserKnowledge.user_id == user_id
            )
        )
        return result.scalar() or 0.0

    async def count_added_in_period(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ):
        result = await self.session.execute(
            select(UserKnowledge)
            .where(UserKnowledge.user_id == user_id)
            .where(UserKnowledge.last_reviewed >= start)
            .where(UserKnowledge.last_reviewed <= end)
        )
        return len(result.scalars().all())
