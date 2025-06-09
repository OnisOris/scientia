import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")
