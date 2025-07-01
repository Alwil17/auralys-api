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
    )  # Can be None for chat-based recommendations
    suggested_activity = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    was_helpful = Column(Boolean, nullable=True)  # User feedback
    recommendation_type = Column(
        String, default="mood_based"
    )  # "mood_based", "chat_based", "manual"
    confidence_score = Column(
        String, nullable=True
    )  # How confident we are in this recommendation

    # Relations
    user = relationship("User", back_populates="recommendations")
    mood_entry = relationship("MoodEntry", back_populates="recommendations")
