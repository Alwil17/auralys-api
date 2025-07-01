from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class RecommendationBase(BaseModel):
    suggested_activity: str = Field(
        ..., min_length=1, max_length=500, description="Activité recommandée"
    )
    recommendation_type: Literal["mood_based", "chat_based", "manual"] = Field(
        default="mood_based", description="Type de recommandation"
    )
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Score de confiance (0-1)"
    )


class RecommendationCreate(RecommendationBase):
    mood_id: Optional[str] = Field(None, description="ID de l'entrée d'humeur associée")


class RecommendationUpdate(BaseModel):
    was_helpful: Optional[bool] = Field(None, description="Feedback utilisateur sur l'utilité")


class RecommendationOut(RecommendationBase):
    id: str
    user_id: str
    mood_id: Optional[str]
    timestamp: datetime
    was_helpful: Optional[bool]

    model_config = ConfigDict(from_attributes=True)


class RecommendationGenerateRequest(BaseModel):
    mood_id: Optional[str] = Field(None, description="ID de l'entrée d'humeur pour générer des recommandations")
    mood_level: Optional[int] = Field(None, ge=1, le=5, description="Niveau d'humeur direct (1-5)")
    activity_preferences: Optional[list[str]] = Field(
        default_factory=list, description="Préférences d'activités de l'utilisateur"
    )
    time_available: Optional[int] = Field(
        None, ge=5, le=240, description="Temps disponible en minutes"
    )


class RecommendationStats(BaseModel):
    total_recommendations: int
    helpful_count: int
    not_helpful_count: int
    pending_feedback: int
    helpfulness_rate: float
    most_recommended_activity: Optional[str]
    period_start: str
    period_end: str


class ActivitySuggestion(BaseModel):
    """Suggestion d'activité avec métadonnées"""
    activity: str
    description: str
    estimated_time: int  # en minutes
    mood_impact: str  # "positive", "calming", "energizing"
    difficulty: Literal["easy", "medium", "hard"]
    category: str  # "physical", "mental", "social", "creative"
    not_helpful_count: int
    pending_feedback_count: int
    helpfulness_rate: float
    most_recommended_activity: Optional[str]
    period_start: str
    period_end: str


class ActivitySuggestion(BaseModel):
    """Suggestion d'activité avec contexte"""

    activity: str = Field(..., description="Description de l'activité")
    category: str = Field(..., description="Catégorie (physical, mental, social, etc.)")
    duration: str = Field(..., description="Durée estimée")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Niveau de difficulté"
    )
    mood_benefit: str = Field(..., description="Bénéfice attendu sur l'humeur")
    instructions: Optional[str] = Field(None, description="Instructions détaillées")


class RecommendationEngine(BaseModel):
    """Réponse du moteur de recommandations"""

    recommendations: list[ActivitySuggestion]
    reasoning: str = Field(
        ..., description="Explication de pourquoi ces activités ont été suggérées"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Score de confiance de la recommandation"
    )
    follow_up_suggestions: Optional[list[str]] = Field(
        default_factory=list, description="Suggestions de suivi"
    )
