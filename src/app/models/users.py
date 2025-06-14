import uuid

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hashed_password: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=True
    )
    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    is_premium: Mapped[bool] = mapped_column(default=False)
    confirmed: Mapped[bool] = mapped_column(default=False)
    # knowledge = relationship(
    #     "UserKnowledge", back_populates="user", cascade="all, delete"
    # )
    # retention_logs = relationship(
    #     "RetentionLog", back_populates="user", cascade="all, delete"
    # )
