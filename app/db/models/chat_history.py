from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.models.base import Base
import uuid


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    message = Column(String, nullable=False)
    sender = Column(String, nullable=False)  # 'user' ou 'bot'
    mood_detected = Column(String, nullable=True)  # Résultat de l'analyse NLP
    collected = Column(Boolean, default=True)  # cloud sync flag

    # Relation avec User
    user = relationship("User", back_populates="chat_history")
