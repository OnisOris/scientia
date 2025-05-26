from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base
from app.models.auth_methods import AuthMethod
from app.models.user_domains import UserDomain


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=True
    )

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    auth_methods: Mapped[list[AuthMethod]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    user_domains: Mapped[list[UserDomain]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    confirmed: Mapped[bool] = mapped_column(default=False)
    is_premium: Mapped[bool] = mapped_column(default=False)
