from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List
import random

from app.db.models.user import User
from app.db.models.mood_entry import MoodEntry
from app.core.security import hash_password


class DataSeeder:
    """Utilitaire pour créer des données de test"""

    def __init__(self, db: Session):
        self.db = db

    def create_test_user(
        self,
        email: str = "test@example.com",
        name: str = "Test User",
        consent: bool = True,
    ) -> User:
        """Créer un utilisateur de test"""
        user = User(
            email=email,
            name=name,
            hashed_password=hash_password("testpassword123"),
            consent=consent,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def create_realistic_mood_data(
        self, user_id: str, days: int = 30
    ) -> List[MoodEntry]:
        """
        Créer des données d'humeur réalistes avec des patterns
        - Weekends généralement meilleurs
        - Variation naturelle
        - Corrélation entre sommeil et humeur
        """
        mood_entries = []
        base_date = datetime.now().date()

        # Patterns réalistes
        weekend_boost = [0, 0, 0, 0, 0, 1, 1]  # Boost weekend (sam/dim)
        activities_weekday = ["Travail", "Réunions", "Formation", "Projet"]
        activities_weekend = ["Famille", "Sport", "Loisirs", "Repos", "Social"]

        for i in range(days):
            date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            day_of_week = (base_date - timedelta(days=i)).weekday()
            mood_entry = self._generate_mood_entry(
                user_id=user_id,
                date=date,
                day_of_week=day_of_week,
                weekend_boost=weekend_boost,
                activities_weekday=activities_weekday,
                activities_weekend=activities_weekend,
            )
            self.db.add(mood_entry)
            mood_entries.append(mood_entry)

        self.db.commit()

        for entry in mood_entries:
            self.db.refresh(entry)

        return mood_entries

    def _generate_mood_entry(
        self,
        user_id: str,
        date: str,
        day_of_week: int,
        weekend_boost: list,
        activities_weekday: list,
        activities_weekend: list,
    ) -> MoodEntry:
        # Base mood avec variation naturelle
        base_mood = 3 + random.uniform(-0.5, 0.5)

        # Weekend boost
        if weekend_boost[day_of_week]:
            base_mood += random.uniform(0.2, 0.8)

        # Clamp between 1-5
        mood = max(1, min(5, round(base_mood)))

        # Corrélation sommeil/humeur
        if mood >= 4:
            sleep_hours = random.uniform(7.5, 9.0)
            stress = random.randint(1, 2)
        elif mood <= 2:
            sleep_hours = random.uniform(5.0, 6.5)
            stress = random.randint(4, 5)
        else:
            sleep_hours = random.uniform(6.5, 8.0)
            stress = random.randint(2, 4)

        # Activité selon le jour
        if day_of_week < 5:  # Semaine
            activity = random.choice(activities_weekday)
        else:  # Weekend
            activity = random.choice(activities_weekend)

        # Notes réalistes
        notes_templates = [
            f"Journée {['difficile', 'normale', 'correcte', 'bonne', 'excellente'][mood-1]}",
            f"Activité: {activity.lower()}",
            f"Sommeil: {'bien dormi' if sleep_hours >= 7.5 else 'nuit courte'}",
            f"Stress: {'élevé' if stress >= 4 else 'gérable' if stress >= 3 else 'faible'}",
        ]
        notes = f"{random.choice(notes_templates[:2])}, {random.choice(notes_templates[2:])}"

        return MoodEntry(
            user_id=user_id,
            date=date,
            mood=mood,
            notes=notes,
            activity=activity,
            sleep_hours=round(sleep_hours, 1),
            stress_level=stress,
        )

    def create_mood_trend_data(
        self, user_id: str, trend: str = "improving"
    ) -> List[MoodEntry]:
        """
        Créer des données avec une tendance spécifique
        trend: 'improving', 'declining', 'stable'
        """
        mood_entries = []
        base_date = datetime.now().date()
        days = 14

        for i in range(days):
            date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")

            if trend == "improving":
                # Amélioration progressive
                progress = (days - i) / days  # 0 to 1
                mood = max(1, min(5, round(2 + progress * 2.5)))
                stress = max(1, min(5, round(4 - progress * 2)))
            elif trend == "declining":
                # Dégradation progressive
                progress = i / days  # 0 to 1
                mood = max(1, min(5, round(4 - progress * 2)))
                stress = max(1, min(5, round(2 + progress * 2)))
            else:  # stable
                mood = 3
                stress = 3

            sleep_hours = 6.5 + (mood - 1) * 0.5

            mood_entry = MoodEntry(
                user_id=user_id,
                date=date,
                mood=mood,
                notes=f"Tendance {trend} - jour {i+1}",
                activity="Test",
                sleep_hours=sleep_hours,
                stress_level=stress,
            )

            self.db.add(mood_entry)
            mood_entries.append(mood_entry)

        self.db.commit()

        for entry in mood_entries:
            self.db.refresh(entry)

        return mood_entries

    def cleanup_test_data(self):
        """Nettoyer toutes les données de test"""
        self.db.query(MoodEntry).delete()
        self.db.query(User).filter(User.email.like("%test%")).delete()
        self.db.commit()

    def create_test_mood_entry(
        self,
        user_id: str,
        mood: int = 3,
        stress_level: int = 3,
        notes: str = "Test mood entry",
        activity: str = "Test Activity",
        sleep_hours: float = 7.0,
        date: str = None,
    ) -> MoodEntry:
        """Créer une entrée d'humeur de test"""
        if date is None:
            date = datetime.now().date().strftime("%Y-%m-%d")

        mood_entry = MoodEntry(
            user_id=str(user_id),  # Ensure string conversion
            date=date,
            mood=mood,
            stress_level=stress_level,
            notes=notes,
            activity=activity,
            sleep_hours=sleep_hours,
        )

        self.db.add(mood_entry)
        self.db.commit()
        self.db.refresh(mood_entry)

        return mood_entry
