from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime


class RecommendationBase(BaseModel):
    suggested_activity: str = Field(
        ..., min_length=1, max_length=500, description="Activité suggérée"
    )
    mood_id: Optional[str] = Field(None, description="ID de l'entrée d'humeur liée")
    was_helpful: Optional[bool] = Field(
        None,
        description="Feedback utilisateur (True=utile, False=pas utile, None=pas encore évalué)",
    )


class RecommendationCreate(BaseModel):
    suggested_activity: str = Field(
        ..., min_length=1, max_length=500, description="Activité suggérée"
    )
    mood_id: Optional[str] = Field(None, description="ID de l'entrée d'humeur source")


class RecommendationUpdate(BaseModel):
    was_helpful: Optional[bool] = Field(
        None, description="Feedback utilisateur sur l'utilité"
    )


class RecommendationOut(RecommendationBase):
    id: str
    user_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True, extra="allow")


class RecommendationFeedback(BaseModel):
    """DTO pour le feedback utilisateur sur une recommandation"""

    was_helpful: bool = Field(..., description="La recommandation était-elle utile ?")


class RecommendationRequest(BaseModel):
    """DTO pour demander des recommandations basées sur l'humeur"""

    mood_level: Optional[int] = Field(
        None, ge=1, le=5, description="Niveau d'humeur (1-5)"
    )
    stress_level: Optional[int] = Field(
        None, ge=1, le=5, description="Niveau de stress (1-5)"
    )
    activity_preference: Optional[
        Literal["physical", "mental", "social", "creative", "relaxing"]
    ] = Field(None, description="Type d'activité préférée")
    time_available: Optional[Literal["5min", "15min", "30min", "1hour", "2hour+"]] = (
        Field(None, description="Temps disponible pour l'activité")
    )


class RecommendationStats(BaseModel):
    """Statistiques sur les recommandations"""

    total_recommendations: int
    helpful_count: int
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
