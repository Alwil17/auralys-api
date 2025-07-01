import pytest
from app.services.nlp_service import NLPService, get_nlp_service


class TestNLPService:
    """Tests pour le service NLP"""

    def test_nlp_service_singleton(self):
        """Test que le service NLP est un singleton"""
        service1 = get_nlp_service()
        service2 = get_nlp_service()
        assert service1 is service2

    def test_analyze_emotion_basic(self):
        """Test analyse d'émotion basique"""
        nlp_service = get_nlp_service()

        # Test avec un texte positif
        result = nlp_service.analyze_emotion("I am so happy today!")

        assert "emotion" in result
        assert "confidence" in result
        assert "model_used" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_analyze_emotion_negative(self):
        """Test analyse d'émotion négative"""
        nlp_service = get_nlp_service()

        result = nlp_service.analyze_emotion("I feel very sad and lonely")

        assert result["emotion"] in ["négatif", "neutre"]  # Fallback ou NLP

    def test_analyze_emotion_empty_text(self):
        """Test avec texte vide"""
        nlp_service = get_nlp_service()

        result = nlp_service.analyze_emotion("")

        assert result["emotion"] == "neutral"
        assert result["confidence"] == 0.5

    def test_batch_analyze_emotions(self):
        """Test analyse en lot"""
        nlp_service = get_nlp_service()

        texts = ["I am happy!", "I am sad.", "This is neutral."]

        results = nlp_service.batch_analyze_emotions(texts)

        assert len(results) == 3
        for result in results:
            assert "emotion" in result
            assert "confidence" in result

    def test_get_model_info(self):
        """Test récupération des infos du modèle"""
        nlp_service = get_nlp_service()

        info = nlp_service.get_model_info()

        assert "model_name" in info
        assert "model_available" in info
        assert "device" in info
        assert "supported_emotions" in info
        assert isinstance(info["model_available"], bool)
