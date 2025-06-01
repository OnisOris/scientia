import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserDomain(Base):
    __tablename__ = "user_domains"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True
    )
    domain_id: Mapped[int] = mapped_column(
        ForeignKey("public.domains.id", ondelete="CASCADE"), primary_key=True
    )
    level = Column(Integer, nullable=False)
    experience = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    analysis = Column(Text, nullable=True)
    domain = relationship(
        "Domain", back_populates="user_domains", lazy="joined"
    )
    user = relationship("User", back_populates="user_domains")
