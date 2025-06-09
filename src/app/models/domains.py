from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_domains = relationship("UserDomain", back_populates="domain")
    concepts = relationship("Concept", back_populates="domain")
    user_profiles = relationship("UserProfile", back_populates="domain")
