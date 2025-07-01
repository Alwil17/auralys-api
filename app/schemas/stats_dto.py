from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class UserOverallStats(BaseModel):
    """Statistiques générales d'un utilisateur"""

    period_start: str = Field(..., description="Date de début de la période")
    period_end: str = Field(..., description="Date de fin de la période")
    mood_entries_count: int = Field(..., description="Nombre d'entrées d'humeur")
    average_mood: float = Field(..., description="Humeur moyenne")
    average_sleep: Optional[float] = Field(
        None, description="Heures de sommeil moyennes"
    )
    average_stress: Optional[float] = Field(None, description="Niveau de stress moyen")
    chat_messages_count: int = Field(..., description="Nombre de messages de chat")
    recommendations_received: int = Field(..., description="Recommandations reçues")
    recommendations_helpful: int = Field(..., description="Recommandations utiles")
    wellness_score: float = Field(
        ..., ge=0, le=100, description="Score de bien-être global (0-100)"
    )
    insights: List[str] = Field(
        default_factory=list, description="Insights personnalisés"
    )


class WeeklyMoodTrend(BaseModel):
    """Tendance d'humeur hebdomadaire"""

    week_start: str = Field(..., description="Début de la semaine")
    week_end: str = Field(..., description="Fin de la semaine")
    entries_count: int = Field(..., description="Nombre d'entrées cette semaine")
    average_mood: float = Field(..., description="Humeur moyenne de la semaine")
    average_stress: Optional[float] = Field(
        None, description="Stress moyen de la semaine"
    )
    average_sleep: Optional[float] = Field(
        None, description="Sommeil moyen de la semaine"
    )
    mood_trend: Literal["improving", "declining", "stable"] = Field(
        ..., description="Tendance de l'humeur"
    )


class MoodDistribution(BaseModel):
    """Distribution des niveaux d'humeur"""

    total_entries: int = Field(..., description="Nombre total d'entrées")
    mood_1_count: int = Field(..., description="Nombre d'humeurs niveau 1")
    mood_2_count: int = Field(..., description="Nombre d'humeurs niveau 2")
    mood_3_count: int = Field(..., description="Nombre d'humeurs niveau 3")
    mood_4_count: int = Field(..., description="Nombre d'humeurs niveau 4")
    mood_5_count: int = Field(..., description="Nombre d'humeurs niveau 5")
    mood_1_percentage: float = Field(..., description="Pourcentage humeur niveau 1")
    mood_2_percentage: float = Field(..., description="Pourcentage humeur niveau 2")
    mood_3_percentage: float = Field(..., description="Pourcentage humeur niveau 3")
    mood_4_percentage: float = Field(..., description="Pourcentage humeur niveau 4")
    mood_5_percentage: float = Field(..., description="Pourcentage humeur niveau 5")
    most_common_mood: Optional[int] = Field(
        None, description="Niveau d'humeur le plus fréquent"
    )


class ActivityEffectiveness(BaseModel):
    """Efficacité d'une activité recommandée"""

    activity: str = Field(..., description="Nom de l'activité")
    times_recommended: int = Field(..., description="Nombre de fois recommandée")
    times_helpful: int = Field(..., description="Nombre de fois jugée utile")
    effectiveness_rate: float = Field(
        ..., description="Taux d'efficacité en pourcentage"
    )


class WellnessInsights(BaseModel):
    """Insights de bien-être personnalisés"""

    insight_type: Literal["sleep", "stress", "regularity", "trend", "general"] = Field(
        ..., description="Type d'insight"
    )
    message: str = Field(..., description="Message d'insight")
    confidence: float = Field(
        ..., ge=0, le=1, description="Niveau de confiance dans l'insight"
    )
    actionable: bool = Field(
        ..., description="L'insight contient-il une action recommandée"
    )


class DailyMoodEntry(BaseModel):
    """Entrée d'humeur pour les graphiques quotidiens"""

    date: str = Field(..., description="Date de l'entrée")
    mood: Optional[int] = Field(None, description="Niveau d'humeur")
    stress: Optional[int] = Field(None, description="Niveau de stress")
    sleep: Optional[float] = Field(None, description="Heures de sommeil")


class PeriodComparison(BaseModel):
    """Comparaison entre deux périodes"""

    current_period: str = Field(..., description="Période actuelle")
    previous_period: str = Field(..., description="Période précédente")
    current_average_mood: float = Field(
        ..., description="Humeur moyenne période actuelle"
    )
    previous_average_mood: float = Field(
        ..., description="Humeur moyenne période précédente"
    )
    mood_change: float = Field(
        ..., description="Changement d'humeur (positif = amélioration)"
    )
    mood_change_percentage: float = Field(..., description="Pourcentage de changement")
    trend: Literal["much_better", "better", "stable", "worse", "much_worse"] = Field(
        ..., description="Tendance globale"
    )


class StatsOverview(BaseModel):
    """Vue d'ensemble des statistiques pour le dashboard"""

    user_stats: UserOverallStats
    weekly_trends: List[WeeklyMoodTrend]
    mood_distribution: MoodDistribution
    period_comparison: Optional[PeriodComparison] = None
    top_activities: List[ActivityEffectiveness]
    daily_entries: List[DailyMoodEntry]
