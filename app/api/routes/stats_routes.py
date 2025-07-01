from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.base import get_db
from app.services.stats_service import StatsService
from app.schemas.stats_dto import (
    UserOverallStats,
    WeeklyMoodTrend,
    MoodDistribution,
    ActivityEffectiveness,
    StatsOverview,
    PeriodComparison,
    DailyMoodEntry,
)
from app.core.security import get_current_user
from app.db.models.user import User


router = APIRouter(prefix="/stats", tags=["statistics"])

NUMBER_OF_DAYS_TEXT = "Number of days"


def get_stats_service(db: Session = Depends(get_db)) -> StatsService:
    """Dependency injection pour StatsService"""
    return StatsService(db)


@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(
    days: int = Query(
        30, ge=7, le=365, description="Number of days to calculate stats for"
    ),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get an overview of user statistics"""
    # Statistiques générales
    user_stats = stats_service.get_user_overall_stats(current_user.id, days)

    # Tendances hebdomadaires
    weekly_trends = stats_service.get_weekly_mood_trends(current_user.id, weeks=4)

    # Distribution des humeurs
    mood_distribution = stats_service.get_mood_distribution(current_user.id, days)

    # Efficacité des activités
    top_activities = stats_service.get_activity_effectiveness(current_user.id, days)

    # Entrées quotidiennes pour les graphiques
    daily_entries = stats_service.get_daily_mood_entries(current_user.id, days)

    # Comparaison avec la période précédente
    period_comparison = None
    if days >= 14:  # Seulement si on a assez de données
        period_comparison = stats_service.get_period_comparison(current_user.id, days)

    return StatsOverview(
        user_stats=user_stats,
        weekly_trends=weekly_trends,
        mood_distribution=mood_distribution,
        period_comparison=period_comparison,
        top_activities=top_activities[:5],  # Top 5 activités
        daily_entries=daily_entries,
    )


@router.get("/overall", response_model=UserOverallStats)
async def get_overall_stats(
    days: int = Query(
        30, ge=1, le=365, description="Number of days to calculate overall stats"
    ),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get overall user statistics for a specific period"""
    return stats_service.get_user_overall_stats(current_user.id, days)


@router.get("/weekly", response_model=List[WeeklyMoodTrend])
async def get_weekly_trends(
    weeks: int = Query(4, ge=1, le=12, description="Number of weeks to analyze"),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get weekly mood trends for the user"""
    return stats_service.get_weekly_mood_trends(current_user.id, weeks)


@router.get("/mood-distribution", response_model=MoodDistribution)
async def get_mood_distribution(
    days: int = Query(30, ge=7, le=365, description=NUMBER_OF_DAYS_TEXT),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get mood distribution for the user over a specified period"""
    return stats_service.get_mood_distribution(current_user.id, days)


@router.get("/activities", response_model=List[ActivityEffectiveness])
async def get_activity_effectiveness(
    days: int = Query(30, ge=7, le=365, description=NUMBER_OF_DAYS_TEXT),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get effectiveness of activities for the user"""
    return stats_service.get_activity_effectiveness(current_user.id, days)


@router.get("/comparison", response_model=PeriodComparison)
async def get_period_comparison(
    days: int = Query(30, ge=14, le=365, description="Period to compare (in days)"),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Compare with the previous period"""
    comparison = stats_service.get_period_comparison(current_user.id, days)
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unsufficient data for comparison",
        )
    return comparison


@router.get("/daily", response_model=List[DailyMoodEntry])
async def get_daily_entries(
    days: int = Query(30, ge=7, le=90, description=NUMBER_OF_DAYS_TEXT),
    current_user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get daily mood entries for the user"""
    return stats_service.get_daily_mood_entries(current_user.id, days)
