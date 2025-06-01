from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.retention_log import RetentionLog
from .base import GenericRepository
import uuid


class RetentionLogRepository(GenericRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, RetentionLog)

    async def count_by_user_and_period(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ):
        result = await self.session.execute(
            select(RetentionLog)
            .where(RetentionLog.user_id == user_id)
            .where(RetentionLog.timestamp >= start)
            .where(RetentionLog.timestamp <= end)
        )
        return len(result.scalars().all())
