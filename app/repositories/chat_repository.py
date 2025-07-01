from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
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
        translated_message: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> ChatHistory:
        """Créer un nouveau message de chat"""
        
        db_message = ChatHistory(
            user_id=user_id,
            message=message_data.message,
            sender=sender,
            mood_detected=mood_detected,
            language=message_data.language,
            translated_message=translated_message,
            model_used=model_used,
            collected=True  # Par défaut, collecté si consentement
        )
        
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def create_bot_response(
        self,
        user_id: str,
        bot_message: str,
        mood_detected: Optional[str] = None,
        language: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> ChatHistory:
        """Créer une réponse du bot"""
        
        db_message = ChatHistory(
            user_id=user_id,
            message=bot_message,
            sender="bot",
            mood_detected=mood_detected,
            language=language,
            model_used=model_used,
            collected=True
        )
        
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def get_user_chat_history(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[ChatHistory]:
        """Récupérer l'historique de chat d'un utilisateur"""
        return self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id
        ).order_by(desc(ChatHistory.timestamp)).offset(skip).limit(limit).all()

    def get_chat_history_by_date_range(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ChatHistory]:
        """Récupérer l'historique de chat pour une période donnée"""
        return self.db.query(ChatHistory).filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.timestamp >= start_date,
                ChatHistory.timestamp <= end_date
            )
        ).order_by(desc(ChatHistory.timestamp)).all()

    def get_recent_conversation(self, user_id: str, limit: int = 10) -> List[ChatHistory]:
        """Récupérer les messages récents pour le contexte de conversation"""
        return self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id
        ).order_by(desc(ChatHistory.timestamp)).limit(limit).all()

    def get_chat_stats(self, user_id: str, days: int = 30) -> Dict:
        """Calculer les statistiques de chat pour un utilisateur"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        messages = self.get_chat_history_by_date_range(user_id, start_date, end_date)
        
        if not messages:
            return {
                "total_messages": 0,
                "messages_user": 0,
                "messages_bot": 0,
                "most_detected_mood": None,
                "average_messages_per_day": 0.0
            }
        
        user_messages = [m for m in messages if m.sender == "user"]
        bot_messages = [m for m in messages if m.sender == "bot"]
        
        # Analyser les humeurs les plus fréquentes
        moods = [m.mood_detected for m in user_messages if m.mood_detected]
        most_detected_mood = max(set(moods), key=moods.count) if moods else None
        
        return {
            "total_messages": len(messages),
            "messages_user": len(user_messages),
            "messages_bot": len(bot_messages),
            "most_detected_mood": most_detected_mood,
            "average_messages_per_day": len(messages) / days if days > 0 else 0.0
        }

    def delete_user_chat_history(self, user_id: str) -> int:
        """Supprimer tout l'historique de chat d'un utilisateur"""
        deleted_count = self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id
        ).delete()
        self.db.commit()
        return deleted_count
