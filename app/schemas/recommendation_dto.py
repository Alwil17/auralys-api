from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, List, Dict
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
    was_helpful: Optional[bool] = Field(
        None, description="Feedback utilisateur sur l'utilité"
    )


class RecommendationOut(RecommendationBase):
    id: str
    user_id: int
    mood_id: Optional[str]
    timestamp: datetime
    was_helpful: Optional[bool]

    model_config = ConfigDict(from_attributes=True, extra="allow")


class RecommendationGenerateRequest(BaseModel):
    mood_id: Optional[str] = Field(
        None, description="ID de l'entrée d'humeur pour générer des recommandations"
    )
    mood_level: Optional[int] = Field(
        None, ge=1, le=5, description="Niveau d'humeur direct (1-5)"
    )
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

    activity: str = Field(..., description="Description de l'activité")
    description: str = Field(..., description="Description détaillée")
    estimated_time: int = Field(..., description="Temps estimé en minutes")
    mood_impact: str = Field(
        ..., description="Impact sur l'humeur: positive, calming, energizing"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Niveau de difficulté"
    )
    category: str = Field(
        ..., description="Catégorie: physical, mental, social, creative"
    )


class ActivityEffectiveness(BaseModel):
    """Efficacité d'une activité recommandée"""

    activity: str = Field(..., description="Nom de l'activité")
    times_recommended: int = Field(..., description="Nombre de fois recommandée")
    times_helpful: int = Field(..., description="Nombre de fois jugée utile")
    effectiveness_rate: float = Field(
        ..., description="Taux d'efficacité en pourcentage"
    )


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


class FeedbackSummary(BaseModel):
    """Résumé des feedbacks utilisateur"""

    total_feedback: int = Field(..., description="Nombre total de feedbacks")
    helpful_rate: float = Field(
        ..., description="Pourcentage de recommandations utiles"
    )
    most_helpful_activities: List[Dict] = Field(
        default_factory=list, description="Activités les plus utiles"
    )
    least_helpful_activities: List[Dict] = Field(
        default_factory=list, description="Activités les moins utiles"
    )
    feedback_trends: List[Dict] = Field(
        default_factory=list, description="Tendances de feedback par semaine"
    )


class RecommendationWithContext(BaseModel):
    """Recommandation avec contexte d'humeur"""

    recommendation: RecommendationOut
    mood_context: Optional[Dict] = Field(
        None, description="Contexte de l'entrée d'humeur associée"
    )
    feedback_deadline: Optional[datetime] = Field(
        None, description="Date limite suggérée pour le feedback"
    )


class BulkFeedbackUpdate(BaseModel):
    """Mise à jour de feedback en lot"""

    feedbacks: List[Dict] = Field(
        ..., description="Liste des feedbacks à mettre à jour"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        json_schema_extra={
            "example": {
                "feedbacks": [
                    {"recommendation_id": "rec1", "was_helpful": True},
                    {"recommendation_id": "rec2", "was_helpful": False},
                ]
            }
        },
    )


class RecommendationFeedbackStats(BaseModel):
    """Statistiques détaillées des feedbacks"""

    user_id: int
    period_start: str
    period_end: str
    total_recommendations: int
    feedback_given: int
    feedback_pending: int
    overall_helpfulness_rate: float
    activity_breakdown: List[ActivityEffectiveness]
    weekly_trends: List[Dict]
    improvement_suggestions: List[str]
