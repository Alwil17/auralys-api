from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.models.base import Base
import uuid


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    mood_id = Column(
        String, ForeignKey("mood_entries.id"), nullable=True
    )  # Optional link to mood entry
    suggested_activity = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    was_helpful = Column(Boolean, nullable=True)  # Feedback simple: True/False/None

    # Relations
    user = relationship("User", back_populates="recommendations")
    mood_entry = relationship("MoodEntry", back_populates="recommendations")
