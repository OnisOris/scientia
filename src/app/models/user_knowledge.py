import uuid
from sqlalchemy import Column, Float, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserKnowledge(Base):
    __tablename__ = "user_knowledge"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("public.users.id"), primary_key=True
    )
    concept_id = Column(
        Integer, ForeignKey("public.concepts.id"), primary_key=True
    )
    retention = Column(Float, default=0.0)
    last_reviewed = Column(DateTime(timezone=True))
    next_review = Column(DateTime(timezone=True))
    concept = relationship("Concept")
    user = relationship("User")

    __table_args__ = (
        Index("idx_user_knowledge_user_review", "user_id", "next_review"),
        Index("idx_user_knowledge_retention", "retention"),
        Index("idx_user_knowledge_concept", "concept_id"),
    )
