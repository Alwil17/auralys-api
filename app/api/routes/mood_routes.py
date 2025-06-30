from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.base import get_db
from app.repositories.mood_repository import MoodRepository
from app.services.mood_service import MoodService
from app.schemas.mood_dto import (
    MoodEntryCreate,
    MoodEntryUpdate,
    MoodEntryOut,
    MoodEntryStats,
)
from app.core.security import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/moods", tags=["mood"])


def get_mood_service(db: Session = Depends(get_db)) -> MoodService:
    """Dependency injection pour MoodService"""
    mood_repository = MoodRepository(db)
    return MoodService(mood_repository)


@router.post("/", response_model=MoodEntryOut, status_code=status.HTTP_201_CREATED)
async def create_mood_entry(
    mood_data: MoodEntryCreate,
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Créer une nouvelle entrée d'humeur"""
    return mood_service.create_mood_entry(current_user, mood_data)


@router.get("/", response_model=List[MoodEntryOut])
async def get_user_mood_entries(
    skip: int = Query(0, ge=0, description="Nombre d'entrées à ignorer"),
    limit: int = Query(
        100, ge=1, le=100, description="Nombre max d'entrées à retourner"
    ),
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Récupérer les entrées d'humeur de l'utilisateur connecté"""
    if start_date and end_date:
        return mood_service.get_mood_entries_by_date_range(
            current_user.id, start_date, end_date
        )
    else:
        return mood_service.get_user_mood_entries(current_user.id, skip, limit)


@router.get("/stats", response_model=MoodEntryStats)
async def get_mood_stats(
    days: int = Query(
        7, ge=1, le=365, description="Nombre de jours pour les statistiques"
    ),
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Obtenir les statistiques d'humeur de l'utilisateur"""
    return mood_service.get_user_mood_stats(current_user.id, days)


@router.get("/{mood_id}", response_model=MoodEntryOut)
async def get_mood_entry(
    mood_id: str,
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Récupérer une entrée d'humeur spécifique"""
    return mood_service.get_mood_entry_by_id(mood_id, current_user.id)


@router.put("/{mood_id}", response_model=MoodEntryOut)
async def update_mood_entry(
    mood_id: str,
    mood_data: MoodEntryUpdate,
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Mettre à jour une entrée d'humeur"""
    return mood_service.update_mood_entry(mood_id, current_user.id, mood_data)


@router.delete("/{mood_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mood_entry(
    mood_id: str,
    current_user: User = Depends(get_current_user),
    mood_service: MoodService = Depends(get_mood_service),
):
    """Supprimer une entrée d'humeur"""
    success = mood_service.delete_mood_entry(mood_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entrée d'humeur non trouvée"
        )
