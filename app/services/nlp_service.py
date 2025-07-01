from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, Optional, List
import logging
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class NLPService:
    """Service pour l'analyse de sentiment et détection d'humeur via HuggingFace"""
    
    def __init__(self):
        self.emotion_classifier = None
        self.sentiment_classifier = None
        self.model_name = "cardiffnlp/twitter-roberta-base-emotion-multilingual-latest"
        self.sentiment_model = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialiser les modèles NLP"""
        try:
            # Modèle pour la détection d'émotions
            self.emotion_classifier = pipeline(
                "text-classification",
                model=self.model_name,
                tokenizer=self.model_name,
                return_all_scores=True
            )
            
            # Modèle pour l'analyse de sentiment
            self.sentiment_classifier = pipeline(
                "sentiment-analysis",
                model=self.sentiment_model,
                tokenizer=self.sentiment_model,
                return_all_scores=True
            )
            
            logger.info("Modèles NLP initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modèles NLP: {e}")
            # Fallback vers des modèles plus légers
            self._initialize_fallback_models()
    
    def _initialize_fallback_models(self):
        """Initialiser des modèles de fallback plus légers"""
        try:
            self.emotion_classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                return_all_scores=True
            )
            
            self.sentiment_classifier = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                return_all_scores=True
            )
            
            self.model_name = "j-hartmann/emotion-english-distilroberta-base"
            logger.info("Modèles NLP de fallback initialisés")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modèles de fallback: {e}")
            self.emotion_classifier = None
            self.sentiment_classifier = None
    
    async def analyze_mood_from_text(self, text: str, language: str = "en") -> Dict:
        """
        Analyser l'humeur d'un texte
        
        Args:
            text: Texte à analyser
            language: Langue du texte (pour l'instant principalement 'en' et 'fr')
        
        Returns:
            Dict contenant l'analyse de l'humeur
        """
        if not self.emotion_classifier:
            return {
                "mood_detected": "neutral",
                "confidence": 0.0,
                "emotions": {},
                "sentiment": "neutral",
                "model_used": "none",
                "error": "Modèle NLP non disponible"
            }
        
        try:
            # Préprocesser le texte
            processed_text = self._preprocess_text(text)
            
            # Analyse des émotions
            emotion_results = await self._analyze_emotions(processed_text)
            
            # Analyse du sentiment
            sentiment_results = await self._analyze_sentiment(processed_text)
            
            # Mapper les émotions vers des humeurs simples
            mood_detected = self._map_emotions_to_mood(emotion_results)
            
            return {
                "mood_detected": mood_detected,
                "confidence": emotion_results[0]["score"] if emotion_results else 0.0,
                "emotions": {result["label"]: result["score"] for result in emotion_results[:3]},
                "sentiment": sentiment_results[0]["label"] if sentiment_results else "neutral",
                "sentiment_confidence": sentiment_results[0]["score"] if sentiment_results else 0.0,
                "model_used": self.model_name,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse NLP: {e}")
            return {
                "mood_detected": "neutral",
                "confidence": 0.0,
                "emotions": {},
                "sentiment": "neutral",
                "model_used": self.model_name,
                "error": str(e)
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Préprocesser le texte pour l'analyse"""
        # Nettoyer et normaliser le texte
        processed = text.strip()
        
        # Limiter la longueur pour éviter les erreurs de token
        if len(processed) > 512:
            processed = processed[:512]
        
        return processed
    
    async def _analyze_emotions(self, text: str) -> List[Dict]:
        """Analyser les émotions dans le texte"""
        try:
            # Exécuter l'analyse en arrière-plan pour éviter le blocage
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                self.emotion_classifier, 
                text
            )
            
            # Trier par score décroissant
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    results = results[0]
                return sorted(results, key=lambda x: x["score"], reverse=True)
            
            return []
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des émotions: {e}")
            return []
    
    async def _analyze_sentiment(self, text: str) -> List[Dict]:
        """Analyser le sentiment du texte"""
        try:
            if not self.sentiment_classifier:
                return []
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.sentiment_classifier,
                text
            )
            
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    results = results[0]
                return sorted(results, key=lambda x: x["score"], reverse=True)
            
            return []
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du sentiment: {e}")
            return []
    
    def _map_emotions_to_mood(self, emotion_results: List[Dict]) -> str:
        """
        Mapper les émotions détectées vers des humeurs simples (1-5)
        """
        if not emotion_results:
            return "neutral"
        
        primary_emotion = emotion_results[0]["label"].lower()
        
        # Mapping des émotions vers des humeurs numériques
        emotion_to_mood = {
            "joy": "happy",
            "happiness": "happy", 
            "love": "happy",
            "excitement": "happy",
            "optimism": "good",
            "approval": "good",
            "gratitude": "good",
            "pride": "good",
            "relief": "neutral",
            "neutral": "neutral",
            "realization": "neutral",
            "surprise": "neutral",
            "confusion": "neutral",
            "curiosity": "neutral",
            "sadness": "sad",
            "disappointment": "sad",
            "grief": "sad",
            "remorse": "sad",
            "embarrassment": "sad",
            "fear": "anxious",
            "nervousness": "anxious",
            "anxiety": "anxious",
            "anger": "angry",
            "annoyance": "angry",
            "frustration": "angry",
            "disgust": "angry"
        }
        
        return emotion_to_mood.get(primary_emotion, "neutral")
    
    def get_mood_suggestions(self, mood: str, emotions: Dict) -> List[str]:
        """
        Générer des suggestions d'activités basées sur l'humeur détectée
        """
        suggestions_map = {
            "sad": [
                "Prendre quelques minutes pour méditer",
                "Écouter de la musique apaisante",
                "Faire une promenade dans la nature",
                "Appeler un proche",
                "Tenir un journal de gratitude"
            ],
            "anxious": [
                "Pratiquer des exercices de respiration",
                "Faire du yoga ou des étirements",
                "Essayer une méditation guidée",
                "Organiser votre espace de travail",
                "Prendre un bain relaxant"
            ],
            "angry": [
                "Faire de l'exercice physique",
                "Écrire vos pensées dans un journal",
                "Pratiquer la respiration profonde",
                "Écouter de la musique énergique",
                "Faire une activité créative"
            ],
            "happy": [
                "Partager votre joie avec quelqu'un",
                "Pratiquer une activité que vous aimez",
                "Faire du sport ou danser",
                "Planifier quelque chose d'amusant",
                "Aider quelqu'un d'autre"
            ],
            "neutral": [
                "Essayer une nouvelle activité",
                "Lire un livre intéressant",
                "Faire une promenade",
                "Apprendre quelque chose de nouveau",
                "Pratiquer la pleine conscience"
            ]
        }
        
        return suggestions_map.get(mood, suggestions_map["neutral"])


# Instance globale du service NLP
@lru_cache()
def get_nlp_service() -> NLPService:
    """Factory function pour obtenir l'instance du service NLP"""
    return NLPService()
