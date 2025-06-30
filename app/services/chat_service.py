from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_dto import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatBotResponse,
    ChatConversationOut,
    ChatStats
)
from app.db.models.user import User


class ChatService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository

    def send_message(self, user: User, message_data: ChatMessageCreate) -> ChatBotResponse:
        """Traiter un message utilisateur et générer une réponse bot"""
        
        # Vérifier le consentement RGPD
        if not user.consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentement requis pour sauvegarder l'historique de chat"
            )

        # Analyse NLP basique (à améliorer avec HuggingFace)
        mood_detected = self._analyze_mood_simple(message_data.message)
        
        # Sauvegarder le message utilisateur
        user_message = self.chat_repository.create_chat_message(
            user_id=str(user.id),
            message_data=message_data,
            sender="user",
            mood_detected=mood_detected
        )

        # Générer une réponse bot
        bot_response_text = self._generate_bot_response(message_data.message, mood_detected)
        suggestions = self._generate_suggestions(mood_detected)

        # Sauvegarder la réponse bot
        bot_message = self.chat_repository.create_bot_response(
            user_id=str(user.id),
            bot_message=bot_response_text,
            mood_detected=mood_detected
        )

        return ChatBotResponse(
            bot_message=bot_response_text,
            mood_detected=mood_detected,
            suggestions=suggestions
        )

    def get_chat_history(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> ChatConversationOut:
        """Récupérer l'historique de conversation d'un utilisateur"""
        messages = self.chat_repository.get_user_chat_history(user_id, skip, limit)
        
        # Convertir en modèles de sortie
        message_outs = [ChatMessageOut.model_validate(msg) for msg in messages]
        
        # Calculer les dates de début et fin
        start_date = messages[-1].timestamp if messages else None
        end_date = messages[0].timestamp if messages else None
        
        return ChatConversationOut(
            messages=message_outs,
            total_messages=len(message_outs),
            start_date=start_date,
            end_date=end_date
        )

    def get_chat_history_by_date_range(
        self, user_id: str, start_date: str, end_date: str
    ) -> ChatConversationOut:
        """Récupérer l'historique pour une période donnée"""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)  # Fin de journée
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de date invalide. Utiliser YYYY-MM-DD"
            )

        messages = self.chat_repository.get_user_chat_history_by_date_range(
            user_id, start_dt, end_dt
        )
        
        message_outs = [ChatMessageOut.model_validate(msg) for msg in messages]
        
        return ChatConversationOut(
            messages=message_outs,
            total_messages=len(message_outs),
            start_date=start_dt,
            end_date=end_dt
        )

    def get_chat_stats(self, user_id: str, days: int = 7) -> ChatStats:
        """Obtenir les statistiques de chat"""
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de jours doit être entre 1 et 365"
            )

        stats = self.chat_repository.get_user_chat_stats(user_id, days)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        return ChatStats(
            total_messages=stats["total_messages"],
            messages_user=stats["messages_user"],
            messages_bot=stats["messages_bot"],
            most_detected_mood=stats["most_detected_mood"],
            average_messages_per_day=stats["average_messages_per_day"],
            period_start=start_date.strftime('%Y-%m-%d'),
            period_end=end_date.strftime('%Y-%m-%d')
        )

    def delete_user_chat_history(self, user_id: str) -> bool:
        """Supprimer l'historique de chat d'un utilisateur (RGPD)"""
        return self.chat_repository.delete_user_chat_history(user_id)

    def _analyze_mood_simple(self, message: str) -> Optional[str]:
        """Analyse simple de sentiment (à remplacer par HuggingFace)"""
        message_lower = message.lower()
        
        positive_words = ['content', 'heureux', 'bien', 'super', 'génial', 'parfait', 'excellent']
        negative_words = ['triste', 'mal', 'difficile', 'stress', 'anxieux', 'déprimé', 'fatigué']
        neutral_words = ['ok', 'normal', 'ça va', 'moyen']
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        neutral_count = sum(1 for word in neutral_words if word in message_lower)
        
        if positive_count > negative_count and positive_count > neutral_count:
            return "positif"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "négatif"
        elif neutral_count > 0:
            return "neutre"
        else:
            return "indéterminé"

    def _generate_bot_response(self, user_message: str, mood: Optional[str]) -> str:
        """Générer une réponse basique du bot (à améliorer)"""
        if mood == "positif":
            responses = [
                "C'est formidable d'entendre que vous allez bien ! Continuez ainsi.",
                "Je suis content que vous vous sentiez bien aujourd'hui.",
                "Votre énergie positive est contagieuse ! Que puis-je faire pour vous aider davantage ?"
            ]
        elif mood == "négatif":
            responses = [
                "Je comprends que ce soit difficile. Voulez-vous en parler davantage ?",
                "Merci de partager cela avec moi. Comment puis-je vous aider ?",
                "Il est normal d'avoir des moments difficiles. Je suis là pour vous écouter."
            ]
        else:
            responses = [
                "Merci de partager cela avec moi. Comment vous sentez-vous maintenant ?",
                "Je vous écoute. Y a-t-il quelque chose en particulier dont vous aimeriez parler ?",
                "Comment puis-je vous aider aujourd'hui ?"
            ]
        
        import random
        return random.choice(responses)

    def _generate_suggestions(self, mood: Optional[str]) -> List[str]:
        """Générer des suggestions basées sur l'humeur"""
        if mood == "négatif":
            return [
                "Prendre quelques minutes pour respirer profondément",
                "Faire une courte promenade",
                "Écouter de la musique relaxante",
                "Contacter un proche"
            ]
        elif mood == "positif":
            return [
                "Partager cette énergie positive avec quelqu'un",
                "Profiter du moment présent",
                "Planifier une activité que vous aimez"
            ]
        else:
            return [
                "Prendre un moment pour réfléchir à vos sentiments",
                "Faire une activité créative",
                "Essayer une séance de méditation courte"
            ]
