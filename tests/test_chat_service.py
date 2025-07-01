import pytest
from unittest.mock import Mock, AsyncMock

from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_dto import ChatMessageCreate, ChatBotResponse
from app.db.models.user import User
from app.db.models.chat_history import ChatHistory
from fastapi import HTTPException


class TestChatService:
    """Tests pour le service de chat"""

    @pytest.fixture
    def mock_chat_repository(self):
        """Mock du repository de chat"""
        return Mock(spec=ChatRepository)

    @pytest.fixture
    def mock_nlp_service(self):
        """Mock du service NLP"""
        nlp_mock = Mock()
        nlp_mock.analyze_mood_from_text = AsyncMock(
            return_value={
                "mood_detected": "happy",
                "confidence": 0.8,
                "emotions": {"joy": 0.8, "sadness": 0.1},
                "sentiment": "positive",
                "model_used": "test-model",
                "language": "en",
            }
        )
        nlp_mock.get_mood_suggestions = Mock(
            return_value=[
                "Partager votre joie",
                "Faire du sport",
                "Planifier quelque chose d'amusant",
            ]
        )
        return nlp_mock

    @pytest.fixture
    def chat_service(self, mock_chat_repository, mock_nlp_service):
        """Service de chat avec mocks"""
        service = ChatService(mock_chat_repository)
        service.nlp_service = mock_nlp_service
        return service

    @pytest.fixture
    def test_user_with_consent(self):
        """Utilisateur de test avec consentement"""
        user = Mock(spec=User)
        user.id = "user-123"
        user.consent = True
        return user

    @pytest.fixture
    def test_user_no_consent(self):
        """Utilisateur de test sans consentement"""
        user = Mock(spec=User)
        user.id = "user-456"
        user.consent = False
        return user

    @pytest.fixture
    def chat_message_data(self):
        """Données de message de test"""
        return ChatMessageCreate(
            message="Je me sens très heureux aujourd'hui !", language="fr"
        )

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        chat_service,
        test_user_with_consent,
        chat_message_data,
        mock_chat_repository,
        mock_nlp_service,
    ):
        """Test envoi de message réussi"""
        # Mock des retours du repository
        user_message_mock = Mock(spec=ChatHistory)
        bot_message_mock = Mock(spec=ChatHistory)

        mock_chat_repository.create_chat_message.return_value = user_message_mock
        mock_chat_repository.create_bot_response.return_value = bot_message_mock

        # Exécuter
        result = await chat_service.send_message(
            test_user_with_consent, chat_message_data
        )

        # Vérifications
        assert isinstance(result, ChatBotResponse)
        assert result.mood_detected == "happy"
        assert len(result.suggestions) <= 3
        assert result.model_used == "test-model"

        # Vérifier les appels aux mocks
        mock_nlp_service.analyze_mood_from_text.assert_called_once_with(
            chat_message_data.message, "fr"
        )
        mock_chat_repository.create_chat_message.assert_called_once()
        mock_chat_repository.create_bot_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_consent(
        self, chat_service, test_user_no_consent, chat_message_data
    ):
        """Test rejet si pas de consentement"""
        with pytest.raises(HTTPException) as exc_info:
            await chat_service.send_message(test_user_no_consent, chat_message_data)

        assert exc_info.value.status_code == 403
        assert "Consentement requis" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_send_message_nlp_error_fallback(
        self,
        chat_service,
        test_user_with_consent,
        chat_message_data,
        mock_chat_repository,
        mock_nlp_service,
    ):
        """Test fallback en cas d'erreur NLP"""
        # Simuler une erreur NLP
        mock_nlp_service.analyze_mood_from_text.side_effect = Exception("NLP Error")

        user_message_mock = Mock(spec=ChatHistory)
        bot_message_mock = Mock(spec=ChatHistory)

        mock_chat_repository.create_chat_message.return_value = user_message_mock
        mock_chat_repository.create_bot_response.return_value = bot_message_mock

        # Exécuter
        result = await chat_service.send_message(
            test_user_with_consent, chat_message_data
        )

        # Vérifications
        assert isinstance(result, ChatBotResponse)
        assert result.mood_detected == "neutral"
        assert "difficultés à analyser" in result.bot_message
        assert len(result.suggestions) == 3

        # Vérifier que les messages ont quand même été sauvegardés
        assert (
            mock_chat_repository.create_chat_message.call_count == 1
        )  # Only user message
        assert (
            mock_chat_repository.create_bot_response.call_count == 1
        )  # Bot fallback response

    def test_generate_bot_response_happy(self, chat_service):
        """Test génération de réponse pour humeur heureuse"""
        response = chat_service._generate_bot_response("happy", {}, "Je suis content!")

        assert (
            "positif" in response.lower()
            or "heureux" in response.lower()
            or "joie" in response.lower()
        )

    def test_generate_bot_response_sad(self, chat_service):
        """Test génération de réponse pour humeur triste"""
        response = chat_service._generate_bot_response("sad", {}, "Je suis triste")

        assert any(
            word in response.lower()
            for word in ["comprends", "difficile", "normal", "sentiments"]
        )

    def test_generate_bot_response_thank_you(self, chat_service):
        """Test réponse spéciale pour remerciement"""
        response = chat_service._generate_bot_response("neutral", {}, "Merci beaucoup!")

        assert "rien" in response.lower() and "aider" in response.lower()

    def test_generate_bot_response_long_message(self, chat_service):
        """Test réponse pour message long (plus empathique)"""
        long_message = "a" * 150  # Message de plus de 100 caractères
        response = chat_service._generate_bot_response("neutral", {}, long_message)

        # Pour un message long, devrait utiliser la première réponse (plus empathique)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_get_chat_history(self, chat_service, mock_chat_repository):
        """Test récupération de l'historique"""
        # Mock des messages avec des données réelles
        from datetime import datetime

        mock_messages = [
            Mock(
                spec=ChatHistory,
                id="msg-1",
                user_id="user-123",
                message="Premier message",
                sender="user",
                mood_detected="happy",
                translated_message=None,
                language="fr",
                model_used="test-model",
                timestamp=datetime.now(),
                collected=True,
            ),
            Mock(
                spec=ChatHistory,
                id="msg-2",
                user_id="user-123",
                message="Deuxième message",
                sender="bot",
                mood_detected="neutral",
                translated_message=None,
                language="fr",
                model_used="test-model",
                timestamp=datetime.now(),
                collected=True,
            ),
        ]
        mock_chat_repository.get_user_chat_history.return_value = mock_messages

        result = chat_service.get_chat_history("user-123", skip=0, limit=50)

        assert result.total_messages == 2
        assert len(result.messages) == 2
        assert result.messages[0].message == "Premier message"
        assert result.messages[1].message == "Deuxième message"
        mock_chat_repository.get_user_chat_history.assert_called_once_with(
            "user-123", 0, 50
        )

    def test_get_chat_stats_success(self, chat_service, mock_chat_repository):
        """Test récupération des statistiques"""
        mock_stats = {
            "total_messages": 100,
            "messages_user": 50,
            "messages_bot": 50,
            "most_detected_mood": "happy",
            "average_messages_per_day": 3.3,
        }
        mock_chat_repository.get_chat_stats.return_value = mock_stats

        result = chat_service.get_chat_stats("user-123", days=30)

        assert result.total_messages == 100
        assert result.messages_user == 50
        assert result.messages_bot == 50
        assert result.most_detected_mood == "happy"
        assert result.average_messages_per_day == 3.3

    def test_get_chat_stats_invalid_days(self, chat_service):
        """Test validation du paramètre days"""
        with pytest.raises(HTTPException) as exc_info:
            chat_service.get_chat_stats("user-123", days=0)

        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            chat_service.get_chat_stats("user-123", days=400)

        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize(
        "mood,expected_keywords",
        [
            ("happy", ["positif", "heureux", "joie", "bonheur"]),
            ("sad", ["comprends", "difficile", "normal", "aider"]),
            ("anxious", ["stressé", "respiration", "anxiété", "concentrer"]),
            ("angry", ["frustration", "colère", "normal", "canaliser"]),
            ("neutral", ["sentez", "écouter", "accompagner", "partager"]),
        ],
    )
    def test_generate_bot_response_all_moods(
        self, chat_service, mood, expected_keywords
    ):
        """Test génération de réponses pour toutes les humeurs"""
        response = chat_service._generate_bot_response(
            mood, {}, "J'ai l'impression que je vais exploser"
        )

        assert isinstance(response, str)
        assert len(response) > 0
        # Au moins un des mots-clés attendus devrait être présent
        response_lower = response.lower()
        assert any(keyword in response_lower for keyword in expected_keywords)

    @pytest.mark.asyncio
    async def test_send_message_with_different_languages(
        self,
        chat_service,
        test_user_with_consent,
        mock_chat_repository,
        mock_nlp_service,
    ):
        """Test envoi de messages dans différentes langues"""
        languages = ["fr", "en", "es"]

        for lang in languages:
            message_data = ChatMessageCreate(message=f"Hello in {lang}", language=lang)

            user_message_mock = Mock(spec=ChatHistory)
            bot_message_mock = Mock(spec=ChatHistory)

            mock_chat_repository.create_chat_message.return_value = user_message_mock
            mock_chat_repository.create_bot_response.return_value = bot_message_mock

            result = await chat_service.send_message(
                test_user_with_consent, message_data
            )

            assert isinstance(result, ChatBotResponse)
            # Vérifier que la langue a été passée au service NLP
            mock_nlp_service.analyze_mood_from_text.assert_called_with(
                message_data.message, lang
            )
