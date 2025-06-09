from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    domain_id = Column(Integer, ForeignKey("public.domains.id"), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    domain = relationship("Domain", back_populates="concepts")
