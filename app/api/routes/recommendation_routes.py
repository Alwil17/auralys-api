from fastapi import APIRouter, Depends, Query, status
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
    RecommendationStats,
)
from app.schemas.recommendation_dto import FeedbackSummary, BulkFeedbackUpdate
from app.core.security import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def get_recommendation_service(db: Session = Depends(get_db)) -> RecommendationService:
    """Dependency injection for RecommendationService.

    Args:
        db (Session, optional): Database session object. Defaults to a session from the dependency injection of get_db.

    Returns:
        RecommendationService: Instance of the recommendation service initialized with the necessary repositories.
    """
    recommendation_repository = RecommendationRepository(db)
    mood_repository = MoodRepository(db)
    return RecommendationService(recommendation_repository, mood_repository)


@router.post(
    "/generate",
    response_model=List[RecommendationOut],
    status_code=status.HTTP_201_CREATED,
)
async def generate_recommendations(
    request: RecommendationGenerateRequest,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Generate recommendations based on a mood entry.

    Args:
        request (RecommendationGenerateRequest): Informations to generate recommendations.
        current_user (User, optional): Connected user. Defaults to Depends(get_current_user).
        recommendation_service (RecommendationService, optional): Recommendation service to interact with the database and associated repositories. Defaults to the result of the dependency injection of get_recommendation_service.

    Returns:
        List[RecommendationOut]: List of generated recommendations
    """
    return await recommendation_service.generate_recommendations_from_mood(
        current_user, request
    )


@router.get("/", response_model=List[RecommendationOut])
async def get_user_recommendations(
    skip: int = Query(0, ge=0, description="Number of recommendations to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Number of recommendations to return"
    ),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get recommendations for the connected user.

    Args:
        skip (int): Number of recommendations to skip. Defaults to 0.
        limit (int): Number of recommendations to return. Defaults to 50.
        current_user (User): Connected user, obtained from the security dependency.
        recommendation_service (RecommendationService): Recommendation service to interact with the database and associated repositories.

    Returns:
        List[RecommendationOut]: List of recommendations for the user.
    """
    return recommendation_service.get_user_recommendations(current_user.id, skip, limit)


@router.put("/{recommendation_id}/feedback", response_model=RecommendationOut)
async def update_recommendation_feedback(
    recommendation_id: str,
    feedback: RecommendationUpdate,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Update the feedback of a recommendation.

    Args:
        recommendation_id (str): ID of the recommendation.
        feedback (RecommendationUpdate): New feedback to update the recommendation with.
        current_user (User): Connected user, obtained from the security dependency.
        recommendation_service (RecommendationService): Recommendation service to interact with the database and associated repositories.

    Returns:
        RecommendationOut: Updated recommendation.
    """
    return recommendation_service.update_recommendation_feedback(
        recommendation_id, current_user.id, feedback
    )


@router.get("/{recommendation_id}", response_model=RecommendationOut)
async def get_recommendation_by_id(
    recommendation_id: str,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get a recommendation by its ID.

    Args:
        recommendation_id (str): ID of the recommendation.
        current_user (User): Connected user, obtained from the security dependency.
        recommendation_service (RecommendationService): Recommendation service to interact with the database and associated repositories.

    Returns:
        RecommendationOut: Recommendation with the given ID.
    """
    return recommendation_service.get_recommendation_by_id(
        recommendation_id, current_user.id
    )


@router.get("/pending-feedback", response_model=List[RecommendationOut])
async def get_pending_feedback_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Number of recommendation"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get pending feedback recommendations for the connected user.

    Args:
        limit (int): Number of recommendations to return. Defaults to 10.

    Returns:
        List[RecommendationOut]: List of pending feedback recommendations.
    """
    return recommendation_service.get_pending_feedback_recommendations(
        current_user.id, limit
    )


@router.get("/stats", response_model=RecommendationStats)
async def get_recommendation_stats(
    days: int = Query(
        30, ge=1, le=365, description="Number of days to calculate stats for"
    ),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    return recommendation_service.get_recommendation_stats(current_user.id, days)


@router.get("/feedback/summary", response_model=FeedbackSummary)
async def get_feedback_summary(
    days: int = Query(30, ge=7, le=365, description="Period for summary"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get a summary of feedback for recommendations."""
    return recommendation_service.get_feedback_summary(current_user.id, days)


@router.post("/feedback/bulk", response_model=Dict[str, int])
async def update_bulk_feedback(
    bulk_feedback: BulkFeedbackUpdate,
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Update multiple feedbacks for recommendations in bulk."""
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
    days: int = Query(30, ge=7, le=365, description="Period to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Retrieve recommendations marked as helpful."""
    return recommendation_service.get_helpful_recommendations(
        current_user.id, days, limit
    )


@router.get("/not-helpful", response_model=List[RecommendationOut])
async def get_not_helpful_recommendations(
    days: int = Query(30, ge=7, le=365, description="Period to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    current_user: User = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Retrieve recommendations marked as not helpful."""
    return recommendation_service.get_not_helpful_recommendations(
        current_user.id, days, limit
    )
