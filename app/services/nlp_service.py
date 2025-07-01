from typing import Dict, Optional, List
import logging
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)


class NLPService:
    """Service pour l'analyse de sentiment/émotion avec Hugging Face"""

    def __init__(self):
        self.model_name = "j-hartmann/emotion-english-distilroberta-base"
        self.emotion_pipeline = None
        self.tokenizer = None
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialiser le modèle Hugging Face"""
        try:
            logger.info(f"Chargement du modèle NLP: {self.model_name}")

            # Charger le modèle et tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )

            # Créer le pipeline
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                top_k=0,
            )

            logger.info("Modèle NLP chargé avec succès")

        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle NLP: {e}")
            self.emotion_pipeline = None

    def analyze_emotion(self, text: str) -> Dict[str, any]:
        """
        Analyser l'émotion d'un texte

        Returns:
            Dict contenant l'émotion principale, le score de confiance et toutes les émotions
        """
        if not self.emotion_pipeline:
            logger.warning(
                "Modèle NLP non disponible, utilisation de l'analyse basique"
            )
            return self._fallback_emotion_analysis(text)

        try:
            # Préprocessing du texte
            processed_text = self._preprocess_text(text)

            if not processed_text.strip():
                return {
                    "emotion": "neutral",
                    "confidence": 0.5,
                    "all_emotions": {},
                    "model_used": self.model_name,
                }

            # Analyse avec le modèle
            results = self.emotion_pipeline(processed_text)

            # Traiter les résultats
            emotions_dict = {
                result["label"].lower(): result["score"] for result in results[0]
            }

            # Trouver l'émotion dominante
            dominant_emotion = max(emotions_dict.items(), key=lambda x: x[1])

            return {
                "emotion": self._map_emotion_to_mood(dominant_emotion[0]),
                "confidence": round(dominant_emotion[1], 3),
                "all_emotions": {k: round(v, 3) for k, v in emotions_dict.items()},
                "model_used": self.model_name,
                "original_emotion": dominant_emotion[0],
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse NLP: {e}")
            return self._fallback_emotion_analysis(text)

    def _preprocess_text(self, text: str) -> str:
        """Préprocesser le texte pour l'analyse"""
        if not text:
            return ""

        # Nettoyer le texte
        text = text.strip()

        # Limiter la longueur (les modèles ont des limites)
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]

        return text

    def _map_emotion_to_mood(self, emotion: str) -> str:
        """
        Mapper les émotions du modèle vers des catégories d'humeur simples

        Le modèle j-hartmann/emotion-english-distilroberta-base prédit:
        - anger, disgust, fear, joy, neutral, sadness, surprise
        """
        emotion_mapping = {
            "joy": "positif",
            "surprise": "positif",
            "neutral": "neutre",
            "sadness": "négatif",
            "anger": "négatif",
            "disgust": "négatif",
            "fear": "négatif",
        }

        return emotion_mapping.get(emotion.lower(), "neutre")

    def _fallback_emotion_analysis(self, text: str) -> Dict[str, any]:
        """Analyse basique de secours si le modèle NLP n'est pas disponible"""
        text_lower = text.lower()

        positive_words = [
            "content",
            "heureux",
            "bien",
            "super",
            "génial",
            "parfait",
            "excellent",
            "great",
            "happy",
            "good",
            "amazing",
        ]
        negative_words = [
            "triste",
            "mal",
            "difficile",
            "stress",
            "anxieux",
            "déprimé",
            "fatigué",
            "sad",
            "bad",
            "terrible",
            "angry",
            "worried",
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            emotion = "positif"
            confidence = min(0.8, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            emotion = "négatif"
            confidence = min(0.8, 0.5 + (negative_count * 0.1))
        else:
            emotion = "neutre"
            confidence = 0.5

        return {
            "emotion": emotion,
            "confidence": confidence,
            "all_emotions": {},
            "model_used": "fallback_basic_analysis",
            "original_emotion": emotion,
        }

    def batch_analyze_emotions(self, texts: List[str]) -> List[Dict[str, any]]:
        """Analyser plusieurs textes en lot"""
        if not self.emotion_pipeline:
            return [self._fallback_emotion_analysis(text) for text in texts]

        try:
            results = []
            for text in texts:
                result = self.analyze_emotion(text)
                results.append(result)
            return results

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse en lot: {e}")
            return [self._fallback_emotion_analysis(text) for text in texts]

    def get_model_info(self) -> Dict[str, any]:
        """Obtenir des informations sur le modèle chargé"""
        return {
            "model_name": self.model_name,
            "model_available": self.emotion_pipeline is not None,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "supported_emotions": [
                "anger",
                "disgust",
                "fear",
                "joy",
                "neutral",
                "sadness",
                "surprise",
            ],
        }


# Instance globale du service NLP (singleton)
_nlp_service_instance = None


def get_nlp_service() -> NLPService:
    """Obtenir l'instance du service NLP (singleton)"""
    global _nlp_service_instance
    if _nlp_service_instance is None:
        _nlp_service_instance = NLPService()
    return _nlp_service_instance
