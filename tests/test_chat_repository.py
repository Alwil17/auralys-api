import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_dto import ChatMessageCreate
from app.db.models.chat_history import ChatHistory


class TestChatRepository:
    """Tests pour le repository de chat"""

    @pytest.fixture
    def chat_repository(self, db: Session):
        """Repository de chat avec session DB"""
        return ChatRepository(db)

    @pytest.fixture
    def test_user(self, db: Session, test_data_seeder):
        """Utilisateur de test"""
        return test_data_seeder.create_test_user(email="chat@test.com", consent=True)

    def test_create_chat_message(self, chat_repository, test_user, db: Session):
        """Test création d'un message de chat"""
        message_data = ChatMessageCreate(
            message="Bonjour, comment allez-vous ?", language="fr"
        )

        result = chat_repository.create_chat_message(
            user_id=test_user.id,
            message_data=message_data,
            sender="user",
            mood_detected="neutral",
            model_used="test-model",
        )

        assert result.id is not None
        assert result.user_id == str(test_user.id)
        assert result.message == message_data.message
        assert result.sender == "user"
        assert result.mood_detected == "neutral"
        assert result.language == "fr"
        assert result.model_used == "test-model"
        assert result.collected == True

        # Vérifier en base de données
        db_message = db.query(ChatHistory).filter(ChatHistory.id == result.id).first()
        assert db_message is not None
        assert db_message.message == message_data.message

    def test_create_bot_response(self, chat_repository, test_user, db: Session):
        """Test création d'une réponse du bot"""
        result = chat_repository.create_bot_response(
            user_id=test_user.id,
            bot_message="Je vais bien, merci !",
            mood_detected="happy",
            language="fr",
            model_used="test-model",
        )

        assert result.id is not None
        assert result.user_id == str(test_user.id)
        assert result.message == "Je vais bien, merci !"
        assert result.sender == "bot"
        assert result.mood_detected == "happy"
        assert result.language == "fr"

    def test_get_user_chat_history(self, chat_repository, test_user, db: Session):
        """Test récupération de l'historique utilisateur"""
        # Créer plusieurs messages
        messages_data = [
            ("Premier message", "user"),
            ("Réponse du bot", "bot"),
            ("Deuxième message", "user"),
            ("Autre réponse", "bot"),
        ]

        created_messages = []
        for message_text, sender in messages_data:
            if sender == "user":
                message_data = ChatMessageCreate(message=message_text)
                msg = chat_repository.create_chat_message(
                    user_id=test_user.id, message_data=message_data, sender=sender
                )
            else:
                msg = chat_repository.create_bot_response(
                    user_id=test_user.id, bot_message=message_text
                )
            created_messages.append(msg)

        # Récupérer l'historique
        history = chat_repository.get_user_chat_history(test_user.id)

        assert len(history) == 4
        # Vérifier l'ordre (plus récent en premier)
        assert history[0].timestamp >= history[1].timestamp
        assert history[1].timestamp >= history[2].timestamp

        # Test avec pagination
        history_page = chat_repository.get_user_chat_history(
            test_user.id, skip=1, limit=2
        )
        assert len(history_page) == 2

    def test_get_chat_history_by_date_range(self, chat_repository, test_user):
        """Test récupération par plage de dates"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Créer des messages à différentes dates
        message_data = ChatMessageCreate(message="Test message")

        # Message d'aujourd'hui
        msg_today = chat_repository.create_chat_message(
            user_id=test_user.id, message_data=message_data, sender="user"
        )

        # Modifier manuellement la date pour simuler un message d'hier
        msg_today.timestamp = yesterday
        chat_repository.db.commit()

        # Message d'aujourd'hui
        msg_today2 = chat_repository.create_chat_message(
            user_id=test_user.id,
            message_data=ChatMessageCreate(message="Today message"),
            sender="user",
        )

        # Récupérer les messages d'aujourd'hui uniquement
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        messages_today = chat_repository.get_chat_history_by_date_range(
            test_user.id, start_of_today, end_of_today
        )

        assert len(messages_today) == 1
        assert messages_today[0].message == "Today message"

    def test_get_recent_conversation(self, chat_repository, test_user):
        """Test récupération de conversation récente"""
        # Créer 15 messages
        for i in range(15):
            message_data = ChatMessageCreate(message=f"Message {i}")
            chat_repository.create_chat_message(
                user_id=test_user.id, message_data=message_data, sender="user"
            )

        # Récupérer les 10 plus récents
        recent = chat_repository.get_recent_conversation(test_user.id, limit=10)

        assert len(recent) == 10
        # Vérifier l'ordre (plus récent en premier)
        assert "Message 0" in recent[0].message  # Le plus récent

    def test_get_chat_stats(self, chat_repository, test_user):
        """Test calcul des statistiques"""
        # Créer des messages avec différentes humeurs
        user_messages = [
            ("Je suis heureux", "happy"),
            ("Je me sens triste", "sad"),
            ("Ça va bien", "happy"),
            ("Je suis inquiet", "anxious"),
        ]

        for message_text, mood in user_messages:
            message_data = ChatMessageCreate(message=message_text)
            chat_repository.create_chat_message(
                user_id=test_user.id,
                message_data=message_data,
                sender="user",
                mood_detected=mood,
            )

        # Créer quelques réponses de bot
        for i in range(3):
            chat_repository.create_bot_response(
                user_id=test_user.id, bot_message=f"Réponse bot {i}"
            )

        # Calculer les stats
        stats = chat_repository.get_chat_stats(test_user.id, days=30)

        assert stats["total_messages"] == 7  # 4 user + 3 bot
        assert stats["messages_user"] == 4
        assert stats["messages_bot"] == 3
        assert stats["most_detected_mood"] == "happy"  # 2 occurrences
        assert stats["average_messages_per_day"] == 7 / 30

    def test_get_chat_stats_no_data(self, chat_repository, test_user):
        """Test stats avec aucune donnée"""
        stats = chat_repository.get_chat_stats(test_user.id, days=30)

        assert stats["total_messages"] == 0
        assert stats["messages_user"] == 0
        assert stats["messages_bot"] == 0
        assert stats["most_detected_mood"] is None
        assert stats["average_messages_per_day"] == 0.0

    def test_delete_user_chat_history(self, chat_repository, test_user, db: Session):
        """Test suppression de l'historique utilisateur"""
        # Créer quelques messages
        for i in range(5):
            message_data = ChatMessageCreate(message=f"Message {i}")
            chat_repository.create_chat_message(
                user_id=test_user.id, message_data=message_data, sender="user"
            )

        # Vérifier qu'ils existent
        messages_before = chat_repository.get_user_chat_history(test_user.id)
        assert len(messages_before) == 5

        # Supprimer
        deleted_count = chat_repository.delete_user_chat_history(test_user.id)
        assert deleted_count == 5

        # Vérifier qu'ils sont supprimés
        messages_after = chat_repository.get_user_chat_history(test_user.id)
        assert len(messages_after) == 0

    def test_chat_message_with_translation(self, chat_repository, test_user):
        """Test message avec traduction"""
        message_data = ChatMessageCreate(message="Hello, how are you?", language="en")

        result = chat_repository.create_chat_message(
            user_id=test_user.id,
            message_data=message_data,
            sender="user",
            translated_message="Bonjour, comment allez-vous ?",
            model_used="translate-model",
        )

        assert result.message == "Hello, how are you?"
        assert result.translated_message == "Bonjour, comment allez-vous ?"
        assert result.language == "en"
        assert result.model_used == "translate-model"
