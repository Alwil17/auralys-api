from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.models.base import Base
import uuid


class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    mood = Column(Integer, nullable=False)  # 1 à 5
    notes = Column(String, nullable=True)
    activity = Column(String, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    stress_level = Column(Integer, nullable=True)  # 1 à 5
    collected = Column(Boolean, default=True)  # cloud sync flag

    # Relations
    user = relationship("User", back_populates="mood_entries")
    recommendations = relationship("Recommendation", back_populates="mood_entry")

    # Unique constraint to prevent duplicate entries for the same user on the same date
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="unique_user_date_mood"),
    )
