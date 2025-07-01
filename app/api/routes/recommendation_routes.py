from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Dict

from app.db.base import get_db
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.mood_repository import MoodRepository
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation_dto import (
    RecommendationGenerateRequest,
    RecommendationUpdate,
    RecommendationOut,
    RecommendationStats
)
from app.schemas.feedback_dto import FeedbackSummary, BulkFeedbackUpdate
from app.core.security import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    """Dependency injection pour RecommendationService"""
    recommendation_repository = RecommendationRepository(db)
    mood_repository = MoodRepository(db)
    return RecommendationService(recommendation_repository, mood_repository)


@router.post("/generate", response_model=List[RecommendationOut], status_code=status.HTTP_201_CREATED)
async def generate_recommendations(
    request: RecommendationGenerateRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Générer des recommandations basées sur l'humeur"""
    return await recommendation_service.generate_recommendations_from_mood(current_user, request)


@router.get("/", response_model=List[RecommendationOut])
async def get_user_recommendations(
    skip: int = Query(0, ge=0, description="Nombre de recommandations à ignorer"),
    limit: int = Query(50, ge=1, le=100, description="Nombre max de recommandations à retourner"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Récupérer les recommandations de l'utilisateur connecté"""
    return recommendation_service.get_user_recommendations(current_user.id, skip, limit)


@router.put("/{recommendation_id}/feedback", response_model=RecommendationOut)
async def update_recommendation_feedback(
    recommendation_id: str,
    feedback: RecommendationUpdate,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Mettre à jour le feedback d'une recommandation"""
    return recommendation_service.update_recommendation_feedback(
        recommendation_id, current_user.id, feedback
    )


@router.get("/{recommendation_id}", response_model=RecommendationOut)
async def get_recommendation_by_id(
    recommendation_id: str,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Récupérer une recommandation spécifique"""
    return recommendation_service.get_recommendation_by_id(recommendation_id, current_user.id)


@router.get("/pending-feedback", response_model=List[RecommendationOut])
async def get_pending_feedback_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Nombre max de recommandations"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Récupérer les recommandations en attente de feedback"""
    return recommendation_service.get_pending_feedback_recommendations(current_user.id, limit)


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    days: int = Query(30, ge=1, le=365, description="Nombre de jours pour les statistiques"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Obtenir les statistiques de recommandations"""
    return recommendation_service.get_recommendation_stats(current_user.id, days)


@router.get("/feedback/summary", response_model=FeedbackSummary)
async def get_feedback_summary(
    days: int = Query(30, ge=7, le=365, description="Période pour le résumé"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Obtenir un résumé des feedbacks utilisateur"""
    return recommendation_service.get_feedback_summary(current_user.id, days)


@router.post("/feedback/bulk", response_model=Dict[str, int])
async def update_bulk_feedback(
    bulk_feedback: BulkFeedbackUpdate,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Mettre à jour plusieurs feedbacks en une fois"""
    results = {"updated": 0, "errors": 0}
    
    for feedback_item in bulk_feedback.feedbacks:
        try:
            recommendation_id = feedback_item.get("recommendation_id")
            was_helpful = feedback_item.get("was_helpful")
            
            if recommendation_id and was_helpful is not None:
                feedback_update = RecommendationUpdate(was_helpful=was_helpful)
                await recommendation_service.update_recommendation_feedback(
                    recommendation_id, current_user.id, feedback_update
                )
                results["updated"] += 1
            else:
                results["errors"] += 1
        except Exception:
            results["errors"] += 1
    
    return results


@router.get("/helpful", response_model=List[RecommendationOut])
async def get_helpful_recommendations(
    days: int = Query(30, ge=7, le=365, description="Période à analyser"),
    limit: int = Query(10, ge=1, le=50, description="Nombre de recommandations"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Récupérer les recommandations marquées comme utiles"""
    return recommendation_service.get_helpful_recommendations(current_user.id, days, limit)


@router.get("/not-helpful", response_model=List[RecommendationOut])
async def get_not_helpful_recommendations(
    days: int = Query(30, ge=7, le=365, description="Période à analyser"),
    limit: int = Query(10, ge=1, le=50, description="Nombre de recommandations"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service)
):
    """Récupérer les recommandations marquées comme non utiles"""
    return recommendation_service.get_not_helpful_recommendations(current_user.id, days, limit)
