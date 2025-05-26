from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class AuthMethod(Base):
    __tablename__ = "auth_methods"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.users.id")
    )
    method: Mapped[str] = mapped_column(nullable=False)
    provider_id: Mapped[str] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="auth_methods")
