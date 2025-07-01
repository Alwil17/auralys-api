from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.repositories.chat_repository import ChatRepository
from app.services.nlp_service import get_nlp_service
from app.schemas.chat_dto import (
    ChatMessageCreate,
    ChatMessageOut,
    ChatBotResponse,
    ChatConversationOut,
    ChatStats,
)
from app.db.models.user import User


class ChatService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository
        self.nlp_service = get_nlp_service()

    async def send_message(
        self, user: User, message_data: ChatMessageCreate
    ) -> ChatBotResponse:
        """
        Traiter un message utilisateur et générer une réponse du bot
        """
        # Vérifier le consentement RGPD
        if not user.consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentement requis pour utiliser le chatbot",
            )

        try:
            # Analyser l'humeur du message utilisateur
            nlp_analysis = await self.nlp_service.analyze_mood_from_text(
                message_data.message, message_data.language or "en"
            )

            # Sauvegarder le message utilisateur avec l'analyse NLP
            user_message = self.chat_repository.create_chat_message(
                user_id=user.id,
                message_data=message_data,
                sender="user",
                mood_detected=nlp_analysis.get("mood_detected"),
                model_used=nlp_analysis.get("model_used"),
            )

            # Générer une réponse du bot basée sur l'humeur détectée
            bot_response_text = self._generate_bot_response(
                nlp_analysis.get("mood_detected", "neutral"),
                nlp_analysis.get("emotions", {}),
                message_data.message,
            )

            # Sauvegarder la réponse du bot
            bot_message = self.chat_repository.create_bot_response(
                user_id=user.id,
                bot_message=bot_response_text,
                mood_detected=nlp_analysis.get("mood_detected"),
                language=message_data.language,
                model_used=nlp_analysis.get("model_used"),
            )

            # Générer des suggestions d'activités
            suggestions = self.nlp_service.get_mood_suggestions(
                nlp_analysis.get("mood_detected", "neutral"),
                nlp_analysis.get("emotions", {}),
            )

            return ChatBotResponse(
                bot_message=bot_response_text,
                mood_detected=nlp_analysis.get("mood_detected"),
                suggestions=suggestions[:3],  # Limiter à 3 suggestions
                emotion_analysis=nlp_analysis.get("emotions"),
                language_detected=nlp_analysis.get("language"),
                model_used=nlp_analysis.get("model_used"),
            )

        except Exception as e:
            # En cas d'erreur, sauvegarder quand même le message utilisateur
            self.chat_repository.create_chat_message(
                user_id=user.id, message_data=message_data, sender="user"
            )

            # Réponse de fallback
            fallback_response = "Je suis désolé, j'ai des difficultés à analyser votre message en ce moment. Comment vous sentez-vous ?"

            self.chat_repository.create_bot_response(
                user_id=user.id,
                bot_message=fallback_response,
                language=message_data.language,
            )

            return ChatBotResponse(
                bot_message=fallback_response,
                mood_detected="neutral",
                suggestions=[
                    "Prendre une pause",
                    "Faire une promenade",
                    "Boire un verre d'eau",
                ],
            )

    def _generate_bot_response(
        self, mood: str, emotions: dict, original_message: str
    ) -> str:
        """
        Générer une réponse personnalisée du bot basée sur l'humeur détectée
        """
        responses = {
            "happy": [
                "C'est merveilleux de vous voir si positif ! Qu'est-ce qui vous rend si heureux aujourd'hui ?",
                "Votre joie est contagieuse ! Continuez à cultiver ces moments de bonheur.",
                "J'adore votre énergie positive ! Que diriez-vous de partager cette joie avec quelqu'un ?",
            ],
            "sad": [
                "Je comprends que vous traversez un moment difficile. Voulez-vous me parler de ce qui vous préoccupe ?",
                "Il est normal de se sentir triste parfois. Prenez le temps qu'il vous faut pour vous sentir mieux.",
                "Vos sentiments sont valides. Que puis-je faire pour vous aider à vous sentir un peu mieux ?",
            ],
            "anxious": [
                "Je sens que vous êtes un peu stressé. Avez-vous essayé quelques exercices de respiration ?",
                "L'anxiété peut être difficile à gérer. Parlons de ce qui vous préoccupe.",
                "Prenons un moment pour nous concentrer sur le présent. Respirez profondément avec moi.",
            ],
            "angry": [
                "Je comprends votre frustration. Parfois, exprimer ces sentiments peut aider.",
                "La colère est une émotion normale. Qu'est-ce qui vous a mis en colère ?",
                "Prenons un moment pour canaliser cette énergie de manière constructive.",
            ],
            "neutral": [
                "Comment vous sentez-vous aujourd'hui ? Je suis là pour vous écouter.",
                "Merci de partager avec moi. Voulez-vous me parler de votre journée ?",
                "Je suis là pour vous accompagner. Qu'aimeriez-vous explorer ensemble ?",
            ],
        }

        mood_responses = responses.get(mood, responses["neutral"])

        # Sélectionner une réponse basée sur la longueur du message original
        if len(original_message) > 100:
            # Message long, réponse plus empathique
            return mood_responses[0]
        elif any(
            word in original_message.lower()
            for word in ["merci", "thanks", "thank you"]
        ):
            # Message de remerciement
            return "De rien ! Je suis là pour vous aider. Y a-t-il autre chose dont vous aimeriez parler ?"
        else:
            # Réponse standard
            import random

            return random.choice(mood_responses)

    def get_chat_history(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> ChatConversationOut:
        """Récupérer l'historique des conversations"""
        messages = self.chat_repository.get_user_chat_history(user_id, skip, limit)
        message_outs = [ChatMessageOut.model_validate(msg) for msg in messages]

        start_date = messages[-1].timestamp if messages else None
        end_date = messages[0].timestamp if messages else None

        return ChatConversationOut(
            messages=message_outs,
            total_messages=len(messages),
            start_date=start_date,
            end_date=end_date,
        )

    def get_chat_stats(self, user_id: str, days: int = 30) -> ChatStats:
        """Obtenir les statistiques de chat"""
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de jours doit être entre 1 et 365",
            )

        stats = self.chat_repository.get_chat_stats(user_id, days)

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
