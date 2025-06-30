import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.db.models.mood_entry import MoodEntry
from app.db.models.user import User
from app.schemas.mood_dto import MoodEntryCreate


@pytest.fixture
def sample_mood_data() -> List[Dict[str, Any]]:
    """Données d'humeur d'exemple pour les tests"""
    base_date = datetime.now().date()

    return [
        {
            "date": (base_date - timedelta(days=6)).strftime("%Y-%m-%d"),
            "mood": 3,
            "notes": "Journée normale, un peu stressé au travail",
            "activity": "Travail",
            "sleep_hours": 7.5,
            "stress_level": 3,
        },
        {
            "date": (base_date - timedelta(days=5)).strftime("%Y-%m-%d"),
            "mood": 4,
            "notes": "Bonne journée, sport le matin",
            "activity": "Sport + Travail",
            "sleep_hours": 8.0,
            "stress_level": 2,
        },
        {
            "date": (base_date - timedelta(days=4)).strftime("%Y-%m-%d"),
            "mood": 2,
            "notes": "Journée difficile, beaucoup de pression",
            "activity": "Travail intensif",
            "sleep_hours": 6.0,
            "stress_level": 4,
        },
        {
            "date": (base_date - timedelta(days=3)).strftime("%Y-%m-%d"),
            "mood": 5,
            "notes": "Excellente journée, sortie entre amis",
            "activity": "Loisirs",
            "sleep_hours": 8.5,
            "stress_level": 1,
        },
        {
            "date": (base_date - timedelta(days=2)).strftime("%Y-%m-%d"),
            "mood": 3,
            "notes": "Journée tranquille à la maison",
            "activity": "Repos",
            "sleep_hours": 9.0,
            "stress_level": 2,
        },
        {
            "date": (base_date - timedelta(days=1)).strftime("%Y-%m-%d"),
            "mood": 4,
            "notes": "Productive day, feeling good",
            "activity": "Travail créatif",
            "sleep_hours": 7.0,
            "stress_level": 2,
        },
        {
            "date": base_date.strftime("%Y-%m-%d"),
            "mood": 3,
            "notes": "Journée en cours, plutôt bien",
            "activity": "Travail",
            "sleep_hours": 7.5,
            "stress_level": 3,
        },
    ]


@pytest.fixture
def mood_entries_week(
    db: Session, test_user: User, sample_mood_data: List[Dict]
) -> List[MoodEntry]:
    """Créer des entrées d'humeur pour une semaine de test"""
    mood_entries = []

    for mood_data in sample_mood_data:
        mood_entry = MoodEntry(user_id=test_user.id, **mood_data)
        db.add(mood_entry)
        mood_entries.append(mood_entry)

    db.commit()

    for entry in mood_entries:
        db.refresh(entry)

    return mood_entries


@pytest.fixture
def mood_create_data() -> MoodEntryCreate:
    """Données pour créer une nouvelle entrée d'humeur"""
    return MoodEntryCreate(
        date=datetime.now().date().strftime("%Y-%m-%d"),
        mood=4,
        notes="Test mood entry",
        activity="Testing",
        sleep_hours=8.0,
        stress_level=2,
    )


@pytest.fixture
def mood_create_data_minimal() -> MoodEntryCreate:
    """Données minimales pour créer une entrée d'humeur"""
    return MoodEntryCreate(
        date=(datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d"), mood=3
    )


@pytest.fixture
def mood_create_data_invalid_date() -> Dict[str, Any]:
    """Données avec date invalide pour tester la validation"""
    return {"date": "2023-13-45", "mood": 3}  # Date invalide


@pytest.fixture
def mood_create_data_invalid_mood() -> Dict[str, Any]:
    """Données avec humeur invalide pour tester la validation"""
    return {
        "date": datetime.now().date().strftime("%Y-%m-%d"),
        "mood": 6,  # Humeur invalide (doit être 1-5)
    }


def create_test_mood_entries(
    db: Session, user_id: str, num_entries: int = 30
) -> List[MoodEntry]:
    """
    Créer un grand nombre d'entrées d'humeur pour les tests de performance
    """
    mood_entries = []
    base_date = datetime.now().date()

    for i in range(num_entries):
        date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")

        # Variation des données pour plus de réalisme
        mood = (i % 5) + 1
        stress = ((i + 2) % 5) + 1
        sleep = 6.0 + (i % 4)

        activities = ["Travail", "Sport", "Loisirs", "Repos", "Social"]
        activity = activities[i % len(activities)]

        mood_entry = MoodEntry(
            user_id=user_id,
            date=date,
            mood=mood,
            notes=f"Note de test numéro {i+1}",
            activity=activity,
            sleep_hours=sleep,
            stress_level=stress,
        )

        db.add(mood_entry)
        mood_entries.append(mood_entry)

    db.commit()

    for entry in mood_entries:
        db.refresh(entry)

    return mood_entries


def get_mood_stats_expected(mood_entries: List[MoodEntry]) -> Dict[str, Any]:
    """
    Calculer les statistiques attendues pour un ensemble d'entrées d'humeur
    Utile pour valider les calculs dans les tests
    """
    if not mood_entries:
        return {
            "average_mood": 0,
            "average_stress": 0,
            "average_sleep": 0,
            "total_entries": 0,
        }

    total_mood = sum(entry.mood for entry in mood_entries)
    stress_levels = [
        entry.stress_level for entry in mood_entries if entry.stress_level is not None
    ]
    sleep_hours = [
        entry.sleep_hours for entry in mood_entries if entry.sleep_hours is not None
    ]

    return {
        "average_mood": round(total_mood / len(mood_entries), 2),
        "average_stress": (
            round(sum(stress_levels) / len(stress_levels), 2) if stress_levels else None
        ),
        "average_sleep": (
            round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else None
        ),
        "total_entries": len(mood_entries),
    }
