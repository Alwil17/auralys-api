from typing import List, Optional, Dict
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_dto import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatBotResponse,
    ChatConversationOut,
    ChatStats,
)
from app.db.models.user import User
from app.services.nlp_service import get_nlp_service


class ChatService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository
        self.nlp_service = get_nlp_service()

    def send_message(
        self, user: User, message_data: ChatMessageCreate
    ) -> ChatBotResponse:
        """Traiter un message utilisateur et générer une réponse bot"""

        # Vérifier le consentement RGPD
        if not user.consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentement requis pour sauvegarder l'historique de chat",
            )

        # Analyse NLP avec Hugging Face
        emotion_analysis = self.nlp_service.analyze_emotion(message_data.message)
        mood_detected = emotion_analysis["emotion"]

        # Sauvegarder le message utilisateur avec les données NLP
        user_message = self.chat_repository.create_chat_message(
            user_id=str(user.id),
            message_data=message_data,
            sender="user",
            mood_detected=mood_detected,
            nlp_data=emotion_analysis,  # Données supplémentaires
        )

        # Générer une réponse bot basée sur l'émotion détectée
        bot_response_text = self._generate_bot_response(
            message_data.message, emotion_analysis
        )
        suggestions = self._generate_suggestions(mood_detected, emotion_analysis)

        # Sauvegarder la réponse bot
        bot_message = self.chat_repository.create_bot_response(
            user_id=str(user.id),
            bot_message=bot_response_text,
            mood_detected=mood_detected,
        )

        return ChatBotResponse(
            bot_message=bot_response_text,
            mood_detected=mood_detected,
            suggestions=suggestions,
            emotion_analysis=emotion_analysis,  # Inclure l'analyse détaillée
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
            end_date=end_date,
        )

    def get_chat_history_by_date_range(
        self, user_id: str, start_date: str, end_date: str
    ) -> ChatConversationOut:
        """Récupérer l'historique pour une période donnée"""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)  # Fin de journée
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de date invalide. Utiliser YYYY-MM-DD",
            )

        messages = self.chat_repository.get_user_chat_history_by_date_range(
            user_id, start_dt, end_dt
        )

        message_outs = [ChatMessageOut.model_validate(msg) for msg in messages]

        return ChatConversationOut(
            messages=message_outs,
            total_messages=len(message_outs),
            start_date=start_dt,
            end_date=end_dt,
        )

    def get_chat_stats(self, user_id: str, days: int = 7) -> ChatStats:
        """Obtenir les statistiques de chat"""
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de jours doit être entre 1 et 365",
            )

        stats = self.chat_repository.get_user_chat_stats(user_id, days)

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        return ChatStats(
            total_messages=stats["total_messages"],
            messages_user=stats["messages_user"],
            messages_bot=stats["messages_bot"],
            most_detected_mood=stats["most_detected_mood"],
            average_messages_per_day=stats["average_messages_per_day"],
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
        )

    def delete_user_chat_history(self, user_id: str) -> bool:
        """Supprimer l'historique de chat d'un utilisateur (RGPD)"""
        return self.chat_repository.delete_user_chat_history(user_id)

    def _generate_bot_response(
        self, user_message: str, emotion_analysis: Dict[str, any]
    ) -> str:
        """Générer une réponse basée sur l'analyse d'émotion détaillée"""
        emotion = emotion_analysis.get("original_emotion", "neutral")
        confidence = emotion_analysis.get("confidence", 0.5)

        # Réponses spécifiques par émotion
        if emotion == "joy":
            responses = [
                f"Je sens beaucoup de joie dans votre message ! (confiance: {confidence:.1%}) C'est merveilleux !",
                "Votre bonheur est contagieux ! Qu'est-ce qui vous rend si heureux aujourd'hui ?",
                "J'adore cette énergie positive ! Continuez ainsi !",
            ]
        elif emotion == "sadness":
            responses = [
                f"Je perçois de la tristesse dans vos mots (confiance: {confidence:.1%}). Je suis là pour vous écouter.",
                "Il est normal de se sentir triste parfois. Voulez-vous en parler ?",
                "Je comprends que ce soit difficile. Comment puis-je vous aider ?",
            ]
        elif emotion == "anger":
            responses = [
                f"Je sens de la colère (confiance: {confidence:.1%}). Prenons un moment pour respirer ensemble.",
                "La colère peut être difficile à gérer. Que s'est-il passé ?",
                "Je comprends votre frustration. Parlons-en calmement.",
            ]
        elif emotion == "fear":
            responses = [
                f"Je détecte de l'anxiété ou de la peur (confiance: {confidence:.1%}). Vous n'êtes pas seul(e).",
                "L'inquiétude peut être écrasante. Que puis-je faire pour vous rassurer ?",
                "Respirons ensemble. Voulez-vous partager ce qui vous préoccupe ?",
            ]
        elif emotion == "surprise":
            responses = [
                f"Vous semblez surpris(e) ! (confiance: {confidence:.1%}) Que s'est-il passé ?",
                "Quelque chose d'inattendu ? Racontez-moi !",
                "La surprise peut être positive ou déstabilisante. Comment vous sentez-vous ?",
            ]
        else:  # neutral, disgust, etc.
            responses = [
                f"Merci de partager cela avec moi (émotion détectée: {emotion}, confiance: {confidence:.1%}).",
                "Je vous écoute. Comment vous sentez-vous maintenant ?",
                "Comment puis-je vous aider aujourd'hui ?",
            ]

        import random

        return random.choice(responses)

    def _generate_suggestions(
        self, mood: Optional[str], emotion_analysis: Dict[str, any]
    ) -> List[str]:
        """Générer des suggestions basées sur l'analyse d'émotion détaillée"""
        original_emotion = emotion_analysis.get("original_emotion", "neutral")
        confidence = emotion_analysis.get("confidence", 0.5)

        # Suggestions spécifiques par émotion
        if original_emotion == "joy":
            return [
                "Partager cette joie avec vos proches",
                "Noter ce moment positif dans un journal",
                "Planifier une activité que vous aimez encore plus",
                "Prendre une photo ou créer un souvenir de ce moment",
            ]
        elif original_emotion == "sadness":
            return [
                "Prendre quelques minutes pour pleurer si vous en avez besoin",
                "Contacter un ami proche ou un membre de la famille",
                "Écouter de la musique apaisante",
                "Pratiquer l'auto-compassion et la douceur envers soi",
            ]
        elif original_emotion == "anger":
            return [
                "Faire de l'exercice physique pour évacuer la tension",
                "Pratiquer la respiration profonde (4-7-8)",
                "Écrire vos pensées dans un journal",
                "Prendre une douche froide ou chaude selon vos préférences",
            ]
        elif original_emotion == "fear":
            return [
                "Pratiquer des exercices de respiration",
                "Utiliser la technique de mise à la terre (5-4-3-2-1)",
                "Parler à quelqu'un en qui vous avez confiance",
                "Faire une activité rassurante et familière",
            ]
        else:
            return [
                "Prendre un moment pour réfléchir à vos sentiments",
                "Faire une courte méditation ou relaxation",
                "Sortir prendre l'air frais",
                "Boire un thé ou une boisson réconfortante",
            ]
