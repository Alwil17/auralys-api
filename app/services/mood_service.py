from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.repositories.mood_repository import MoodRepository
from app.schemas.mood_dto import (
    MoodEntryCreate,
    MoodEntryUpdate,
    MoodEntryOut,
    MoodEntryStats,
)
from app.db.models.user import User


# Constants for error messages
MOOD_ENTRY_NOT_FOUND_MSG = "Entrée d'humeur non trouvée"
UNAUTHORIZED_ACCESS_MSG = "Accès non autorisé à cette entrée d'humeur"


class MoodService:
    def __init__(self, mood_repository: MoodRepository):
        self.mood_repository = mood_repository

    def create_mood_entry(self, user: User, mood_data: MoodEntryCreate) -> MoodEntryOut:
        """Créer une nouvelle entrée d'humeur avec validation RGPD"""

        # Vérifier le consentement RGPD
        if not user.consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentement requis pour sauvegarder les données d'humeur",
            )

        # Vérifier si une entrée existe déjà pour cette date
        existing_entry = self.mood_repository.get_mood_entry_by_user_and_date(
            user.id, mood_data.date
        )
        if existing_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Une entrée d'humeur existe déjà pour la date {mood_data.date}",
            )

        # Créer l'entrée
        mood_entry = self.mood_repository.create_mood_entry(user.id, mood_data)
        return MoodEntryOut.model_validate(mood_entry)

    def get_user_mood_entries(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[MoodEntryOut]:
        """Récupérer les entrées d'humeur d'un utilisateur"""
        mood_entries = self.mood_repository.get_user_mood_entries(user_id, skip, limit)
        return [MoodEntryOut.model_validate(entry) for entry in mood_entries]

    def get_mood_entry_by_id(self, mood_id: str, user_id: str) -> MoodEntryOut:
        """Récupérer une entrée d'humeur par ID avec vérification de propriété"""
        mood_entry = self.mood_repository.get_mood_entry_by_id(mood_id)

        if not mood_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=MOOD_ENTRY_NOT_FOUND_MSG
            )

        # Convert both IDs to strings for comparison to handle UUID vs string mismatch
        if str(mood_entry.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACCESS_MSG
            )

        return MoodEntryOut.model_validate(mood_entry)

    def update_mood_entry(
        self, mood_id: str, user_id: str, mood_data: MoodEntryUpdate
    ) -> MoodEntryOut:
        """Mettre à jour une entrée d'humeur"""
        # Vérifier l'existence et la propriété
        mood_entry = self.mood_repository.get_mood_entry_by_id(mood_id)

        if not mood_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=MOOD_ENTRY_NOT_FOUND_MSG
            )

        # Convert both IDs to strings for comparison
        if str(mood_entry.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACCESS_MSG
            )

        updated_entry = self.mood_repository.update_mood_entry(mood_id, mood_data)
        return MoodEntryOut.model_validate(updated_entry)

    def delete_mood_entry(self, mood_id: str, user_id: str) -> bool:
        """Supprimer une entrée d'humeur"""
        # Vérifier l'existence et la propriété
        mood_entry = self.mood_repository.get_mood_entry_by_id(mood_id)

        if not mood_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=MOOD_ENTRY_NOT_FOUND_MSG
            )

        # Convert both IDs to strings for comparison
        if str(mood_entry.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACCESS_MSG
            )

        return self.mood_repository.delete_mood_entry(mood_id)

    def get_mood_entries_by_date_range(
        self, user_id: str, start_date: str, end_date: str
    ) -> List[MoodEntryOut]:
        """Récupérer les entrées d'humeur pour une période donnée"""
        try:
            # Valider les formats de date
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de date invalide. Utiliser YYYY-MM-DD",
            )

        mood_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id, start_date, end_date
        )
        return [MoodEntryOut.model_validate(entry) for entry in mood_entries]

    def get_user_mood_stats(self, user_id: str, days: int = 7) -> MoodEntryStats:
        """Calculer les statistiques d'humeur d'un utilisateur"""
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de jours doit être entre 1 et 365",
            )

        stats = self.mood_repository.get_user_mood_stats(user_id, days)

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        return MoodEntryStats(
            average_mood=stats["average_mood"],
            average_stress=stats["average_stress"],
            average_sleep=stats["average_sleep"],
            total_entries=stats["total_entries"],
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
        )
