from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class GenericRepository:
    def __init__(self, session: AsyncSession, model):
        self.session = session
        self.model = model

    async def get_one(self, **kwargs):
        result = await self.session.execute(
            select(self.model).filter_by(**kwargs)
        )
        return result.scalars().first()

    async def add(self, entity):
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def get_all(self):
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def get_by_id(self, id_):
        result = await self.session.execute(
            select(self.model).filter_by(id=id_)
        )
        return result.scalar_one_or_none()

    async def filter_by(self, **kwargs):
        query = select(self.model).where(
            *[
                getattr(self.model, key) == value
                for key, value in kwargs.items()
            ]
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete(self, entity):
        await self.session.delete(entity)
        await self.session.commit()

    async def get_by(self, **kwargs):
        result = await self.session.execute(
            select(self.model).filter_by(**kwargs)
        )
        return result.scalars().all()

    async def get_first(self, **kwargs):
        result = await self.session.execute(
            select(self.model).filter_by(**kwargs).limit(1)
        )
        return result.scalars().first()
