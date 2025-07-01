from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.db.models.chat_history import ChatHistory
from app.schemas.chat_dto import ChatMessageCreate


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_chat_message(
        self,
        user_id: str,
        message_data: ChatMessageCreate,
        sender: str = "user",
        mood_detected: Optional[str] = None,
        nlp_data: Optional[Dict] = None,
    ) -> ChatHistory:
        """Créer un nouveau message de chat"""
        db_message = ChatHistory(
            user_id=user_id,
            message=message_data.message,
            sender=sender,
            mood_detected=mood_detected,
            collected=True,
            model_used=nlp_data.get("model_used", "unknown") if nlp_data else "basic",
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def create_bot_response(
        self, user_id: str, bot_message: str, mood_detected: Optional[str] = None
    ) -> ChatHistory:
        """Créer une réponse du bot"""
        db_message = ChatHistory(
            user_id=user_id,
            message=bot_message,
            sender="bot",
            mood_detected=mood_detected,
            collected=True,
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def get_user_chat_history(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[ChatHistory]:
        """Récupérer l'historique de chat d'un utilisateur"""
        return (
            self.db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(desc(ChatHistory.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_chat_history_by_date_range(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[ChatHistory]:
        """Récupérer l'historique de chat pour une période donnée"""
        return (
            self.db.query(ChatHistory)
            .filter(
                ChatHistory.user_id == user_id,
                ChatHistory.timestamp >= start_date,
                ChatHistory.timestamp <= end_date,
            )
            .order_by(desc(ChatHistory.timestamp))
            .all()
        )

    def get_chat_message_by_id(self, message_id: str) -> Optional[ChatHistory]:
        """Récupérer un message par ID"""
        return self.db.query(ChatHistory).filter(ChatHistory.id == message_id).first()

    def delete_user_chat_history(self, user_id: str) -> bool:
        """Supprimer tout l'historique de chat d'un utilisateur"""
        deleted_count = (
            self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
        )
        self.db.commit()
        return deleted_count > 0

    def get_user_chat_stats(self, user_id: str, days: int = 7) -> dict:
        """Calculer les statistiques de chat pour un utilisateur"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        messages = self.get_user_chat_history_by_date_range(
            user_id, start_date, end_date
        )

        if not messages:
            return {
                "total_messages": 0,
                "messages_user": 0,
                "messages_bot": 0,
                "most_detected_mood": None,
                "average_messages_per_day": 0.0,
            }

        user_messages = [msg for msg in messages if msg.sender == "user"]
        bot_messages = [msg for msg in messages if msg.sender == "bot"]

        # Analyser les humeurs détectées
        moods = [msg.mood_detected for msg in messages if msg.mood_detected]
        most_detected_mood = max(set(moods), key=moods.count) if moods else None

        return {
            "total_messages": len(messages),
            "messages_user": len(user_messages),
            "messages_bot": len(bot_messages),
            "most_detected_mood": most_detected_mood,
            "average_messages_per_day": round(len(messages) / days, 2),
        }
