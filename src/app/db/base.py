from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    __table_args__ = {"schema": "public"}

    def __repr__(self):
        return f"<{self.__class__.__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_'))})>"


# Need for normal creating db tables:
from app.models import users
from app.models import user_profile
from app.models import auth_methods
from app.models import domains
from app.models import user_domains
