from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    DateTime,
)
from sqlalchemy.orm import relationship
from app.db.models.base import Base
import uuid
from datetime import datetime, timezone


class MoodEntry(Base):
    __tablename__ = "mood_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  # Format YYYY-MM-DD
    mood = Column(Integer, nullable=False)  # 1-5 scale
    notes = Column(String, nullable=True)
    activity = Column(String, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    stress_level = Column(Integer, nullable=True)  # 1-5 scale
    collected = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relations
    user = relationship("User", back_populates="mood_entries")
    recommendations = relationship("Recommendation", back_populates="mood_entry")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if isinstance(self.date, str):
            # Convert string date to datetime object
            from datetime import datetime

            self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
    
    def __repr__(self):
        return f"<MoodEntry(id={self.id}, user_id={self.user_id}, date={self.date}, mood={self.mood})>"
    
    # Unique constraint to prevent duplicate entries for the same user on the same date
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="unique_user_date_mood"),
    )
