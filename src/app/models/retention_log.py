import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class RetentionLog(Base):
    __tablename__ = "retention_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id"))
    concept_id = Column(Integer, ForeignKey("public.concepts.id"))
    old_lambda = Column(Float)
    new_lambda = Column(Float)
    retention_before = Column(Float)
    retention_after = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    concept = relationship("Concept")
    user = relationship("User")
    __table_args__ = (
        UniqueConstraint(
            "user_id", "concept_id", "timestamp", name="uq_user_concept_date"
        ),
        Index("idx_retention_log_concept", "concept_id"),
    )
