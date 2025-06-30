from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.models.mood_entry import MoodEntry
from app.schemas.mood_dto import MoodEntryCreate, MoodEntryUpdate


class MoodRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_mood_entry(self, user_id: str, mood_data: MoodEntryCreate) -> MoodEntry:
        """Créer une nouvelle entrée d'humeur"""
        db_mood = MoodEntry(
            user_id=user_id,
            **mood_data.dict()
        )
        self.db.add(db_mood)
        self.db.commit()
        self.db.refresh(db_mood)
        return db_mood

    def get_mood_entry_by_id(self, mood_id: str) -> Optional[MoodEntry]:
        """Récupérer une entrée d'humeur par ID"""
        return self.db.query(MoodEntry).filter(MoodEntry.id == mood_id).first()

    def get_mood_entry_by_user_and_date(self, user_id: str, date: str) -> Optional[MoodEntry]:
        """Récupérer une entrée d'humeur par utilisateur et date"""
        return self.db.query(MoodEntry).filter(
            and_(MoodEntry.user_id == user_id, MoodEntry.date == date)
        ).first()

    def get_user_mood_entries(self, user_id: str, skip: int = 0, limit: int = 100) -> List[MoodEntry]:
        """Récupérer toutes les entrées d'humeur d'un utilisateur"""
        return self.db.query(MoodEntry).filter(
            MoodEntry.user_id == user_id
        ).order_by(desc(MoodEntry.date)).offset(skip).limit(limit).all()

    def get_user_mood_entries_by_date_range(
        self, user_id: str, start_date: str, end_date: str
    ) -> List[MoodEntry]:
        """Récupérer les entrées d'humeur d'un utilisateur pour une période donnée"""
        return self.db.query(MoodEntry).filter(
            and_(
                MoodEntry.user_id == user_id,
                MoodEntry.date >= start_date,
                MoodEntry.date <= end_date
            )
        ).order_by(desc(MoodEntry.date)).all()

    def update_mood_entry(self, mood_id: str, mood_data: MoodEntryUpdate) -> Optional[MoodEntry]:
        """Mettre à jour une entrée d'humeur"""
        db_mood = self.get_mood_entry_by_id(mood_id)
        if db_mood:
            update_data = mood_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_mood, field, value)
            self.db.commit()
            self.db.refresh(db_mood)
        return db_mood

    def delete_mood_entry(self, mood_id: str) -> bool:
        """Supprimer une entrée d'humeur"""
        db_mood = self.get_mood_entry_by_id(mood_id)
        if db_mood:
            self.db.delete(db_mood)
            self.db.commit()
            return True
        return False

    def get_user_mood_stats(self, user_id: str, days: int = 7) -> dict:
        """Calculer les statistiques d'humeur pour un utilisateur"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        moods = self.get_user_mood_entries_by_date_range(
            user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        )
        
        if not moods:
            return {
                "average_mood": 0,
                "average_stress": 0,
                "average_sleep": 0,
                "total_entries": 0
            }
        
        total_mood = sum(mood.mood for mood in moods)
        stress_levels = [mood.stress_level for mood in moods if mood.stress_level is not None]
        sleep_hours = [mood.sleep_hours for mood in moods if mood.sleep_hours is not None]
        
        return {
            "average_mood": round(total_mood / len(moods), 2),
            "average_stress": round(sum(stress_levels) / len(stress_levels), 2) if stress_levels else None,
            "average_sleep": round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else None,
            "total_entries": len(moods)
        }
