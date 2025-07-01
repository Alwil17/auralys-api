import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.nlp_service import NLPService, get_nlp_service


class TestNLPService:
    """Tests pour le service NLP"""

    def test_nlp_service_singleton(self):
        """Test que le service NLP est un singleton"""
        service1 = get_nlp_service()
        service2 = get_nlp_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_analyze_mood_from_text_basic(self):
        """Test analyse d'humeur basique"""
        nlp_service = get_nlp_service()

        # Test avec un texte positif
        result = await nlp_service.analyze_mood_from_text("I am so happy today!")

        assert "mood_detected" in result
        assert "confidence" in result
        assert "model_used" in result
        assert "emotions" in result
        assert "sentiment" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_analyze_mood_from_text_negative(self):
        """Test analyse d'émotion négative"""
        nlp_service = get_nlp_service()

        result = await nlp_service.analyze_mood_from_text("I feel very sad and lonely")

        assert result["mood_detected"] in ["sad", "neutral", "angry", "anxious"]
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_analyze_mood_from_text_empty(self):
        """Test avec texte vide"""
        nlp_service = get_nlp_service()

        result = await nlp_service.analyze_mood_from_text("")

        # Should handle empty text gracefully
        assert "mood_detected" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_analyze_mood_with_language(self):
        """Test analyse avec spécification de langue"""
        nlp_service = get_nlp_service()

        result = await nlp_service.analyze_mood_from_text(
            "Je suis très heureux", language="fr"
        )

        assert result["language"] == "fr"
        assert "mood_detected" in result

    def test_preprocess_text(self):
        """Test du préprocessing de texte"""
        nlp_service = get_nlp_service()

        # Test texte normal
        processed = nlp_service._preprocess_text("  Hello world!  ")
        assert processed == "Hello world!"

        # Test texte très long
        long_text = "a" * 600
        processed = nlp_service._preprocess_text(long_text)
        assert len(processed) <= 512

    def test_map_emotions_to_mood(self):
        """Test du mapping des émotions vers les humeurs"""
        nlp_service = get_nlp_service()

        # Test avec résultats d'émotions simulés
        emotion_results = [
            {"label": "joy", "score": 0.8},
            {"label": "sadness", "score": 0.2},
        ]

        mood = nlp_service._map_emotions_to_mood(emotion_results)
        assert mood == "happy"

        # Test avec émotion négative
        emotion_results = [
            {"label": "sadness", "score": 0.9},
            {"label": "joy", "score": 0.1},
        ]

        mood = nlp_service._map_emotions_to_mood(emotion_results)
        assert mood == "sad"

        # Test avec liste vide
        mood = nlp_service._map_emotions_to_mood([])
        assert mood == "neutral"

    def test_get_mood_suggestions(self):
        """Test génération de suggestions basées sur l'humeur"""
        nlp_service = get_nlp_service()

        # Test pour chaque type d'humeur
        moods = ["happy", "sad", "anxious", "angry", "neutral"]

        for mood in moods:
            suggestions = nlp_service.get_mood_suggestions(mood, {})
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            assert all(isinstance(s, str) for s in suggestions)

        # Test avec humeur inconnue
        suggestions = nlp_service.get_mood_suggestions("unknown_mood", {})
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    @patch("app.services.nlp_service.logger")
    async def test_analyze_mood_with_error_handling(self, mock_logger):
        """Test gestion d'erreur lors de l'analyse"""
        nlp_service = NLPService()

        # Simuler une erreur en désactivant les modèles
        nlp_service.emotion_classifier = None
        nlp_service.sentiment_classifier = None

        result = await nlp_service.analyze_mood_from_text("Test message")

        assert result["mood_detected"] == "neutral"
        assert result["confidence"] == 0.0
        assert "error" in result
        assert result["model_used"] == "none"

    @pytest.mark.asyncio
    async def test_analyze_emotions_async(self):
        """Test que l'analyse d'émotions est bien asynchrone"""
        nlp_service = get_nlp_service()

        if nlp_service.emotion_classifier:
            # Test que la méthode est bien asynchrone
            result = await nlp_service._analyze_emotions("I am happy")
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_sentiment_async(self):
        """Test que l'analyse de sentiment est bien asynchrone"""
        nlp_service = get_nlp_service()

        if nlp_service.sentiment_classifier:
            result = await nlp_service._analyze_sentiment("I am happy")
            assert isinstance(result, list)

    def test_emotion_to_mood_mapping_completeness(self):
        """Test que tous les mappings d'émotions sont couverts"""
        nlp_service = get_nlp_service()

        # Test des émotions communes
        test_emotions = [
            {"label": "joy", "score": 0.8},
            {"label": "sadness", "score": 0.8},
            {"label": "anger", "score": 0.8},
            {"label": "fear", "score": 0.8},
            {"label": "surprise", "score": 0.8},
            {"label": "disgust", "score": 0.8},
            {"label": "neutral", "score": 0.8},
        ]

        for emotion_result in test_emotions:
            mood = nlp_service._map_emotions_to_mood([emotion_result])
            assert mood in ["happy", "sad", "angry", "anxious", "neutral", "good"]

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """Test analyses simultanées"""
        nlp_service = get_nlp_service()

        texts = [
            "I am very happy today!",
            "I feel sad and lonely",
            "This makes me angry",
            "I am worried about tomorrow",
        ]

        # Lancer les analyses en parallèle
        tasks = [nlp_service.analyze_mood_from_text(text) for text in texts]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        for result in results:
            assert "mood_detected" in result
            assert "confidence" in result

    def test_model_initialization_fallback(self):
        """Test du fallback lors de l'initialisation des modèles"""
        # Créer une nouvelle instance pour tester l'initialisation
        with patch("app.services.nlp_service.pipeline") as mock_pipeline:
            # Simuler une erreur lors du chargement du modèle principal
            mock_pipeline.side_effect = [Exception("Model not found"), Mock(), Mock()]

            nlp_service = NLPService()

            # Vérifier que le fallback a été appelé
            assert (
                mock_pipeline.call_count >= 2
            )  # Au moins un appel pour le modèle principal et le fallback
