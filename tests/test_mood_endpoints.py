import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any

from app.main import app
from app.db.models.user import User
from app.db.models.mood_entry import MoodEntry
from tests.utils.test_data_seeder import TestDataSeeder

client = TestClient(app)


class TestMoodSubmission:
    """Tests pour la soumission d'entrées d'humeur"""

    def test_create_mood_entry_success(
        self,
        db: Session,
        test_user_with_consent: User,
        mood_create_data: Dict[str, Any],
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test création réussie d'une entrée d'humeur"""
        response = client.post(
            "/moods/",
            json=mood_create_data.model_dump(),
            headers=auth_headers_with_consent,
        )

        assert response.status_code == 201
        data = response.json()

        # Vérifier la structure de la réponse
        assert "id" in data
        assert data["user_id"] == str(test_user_with_consent.id)
        assert data["date"] == mood_create_data.date
        assert data["mood"] == mood_create_data.mood
        assert data["notes"] == mood_create_data.notes
        assert data["activity"] == mood_create_data.activity
        assert data["sleep_hours"] == mood_create_data.sleep_hours
        assert data["stress_level"] == mood_create_data.stress_level
        assert data["collected"] == True

        # Vérifier en base de données
        db_mood = db.query(MoodEntry).filter(MoodEntry.id == data["id"]).first()

        assert db_mood is not None
        assert db_mood.user_id == str(test_user_with_consent.id)

    def test_create_mood_entry_minimal_data(
        self,
        mood_create_data_minimal: Dict[str, Any],
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test création avec données minimales"""
        response = client.post(
            "/moods/",
            json=mood_create_data_minimal.model_dump(),
            headers=auth_headers_with_consent,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["mood"] == mood_create_data_minimal.mood
        assert data["notes"] is None
        assert data["activity"] is None
        assert data["sleep_hours"] is None
        assert data["stress_level"] is None

    def test_create_mood_entry_duplicate_date(
        self,
        mood_create_data: Dict[str, Any],
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test erreur pour date dupliquée"""
        # Créer la première entrée
        client.post(
            "/moods/",
            json=mood_create_data.model_dump(),
            headers=auth_headers_with_consent,
        )

        # Tentative de création d'une seconde entrée pour la même date
        response = client.post(
            "/moods/",
            json=mood_create_data.model_dump(),
            headers=auth_headers_with_consent,
        )

        assert response.status_code == 400
        assert "existe déjà" in response.json()["detail"]

    def test_create_mood_entry_no_consent(
        self,
        mood_create_data: Dict[str, Any],
        auth_headers_no_consent: Dict[str, str],
    ):
        """Test rejet si pas de consentement RGPD"""
        response = client.post(
            "/moods/",
            json=mood_create_data.model_dump(),
            headers=auth_headers_no_consent,
        )

        assert response.status_code == 403
        assert "Consentement requis" in response.json()["detail"]

    def test_create_mood_entry_invalid_data(
        self, auth_headers_with_consent: Dict[str, str]
    ):
        """Test validation des données invalides"""
        # Test mood invalide (hors range 1-5)
        invalid_data = {"date": datetime.now().date().strftime("%Y-%m-%d"), "mood": 6}

        response = client.post(
            "/moods/", json=invalid_data, headers=auth_headers_with_consent
        )
        assert response.status_code == 422

        # Test date invalide
        invalid_data = {"date": "2023-13-45", "mood": 3}

        response = client.post(
            "/moods/", json=invalid_data, headers=auth_headers_with_consent
        )
        assert response.status_code == 422

    def test_create_mood_entry_unauthorized(self, mood_create_data: Dict[str, Any]):
        """Test accès non autorisé"""
        response = client.post("/moods/", json=mood_create_data.model_dump())
        print(response.json())
        assert response.status_code == 401


class TestMoodListing:
    """Tests pour la récupération des entrées d'humeur"""

    def test_get_user_mood_entries_success(
        self,
        test_user_with_consent: User,
        mood_entries_week: list,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test récupération réussie des entrées d'humeur"""
        response = client.get("/moods/", headers=auth_headers_with_consent)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(mood_entries_week)

        # Vérifier que les entrées sont triées par date (desc)
        dates = [entry["date"] for entry in data]
        assert dates == sorted(dates, reverse=True)

        # Vérifier la structure des données
        for entry in data:
            assert "id" in entry
            assert "user_id" in str(entry)
            assert "date" in entry
            assert "mood" in entry
            assert entry["user_id"] == str(test_user_with_consent.id)

    def test_get_mood_entries_pagination(
        self,
        test_user_with_consent: User,
        auth_headers_with_consent: Dict[str, str],
        test_data_seeder: TestDataSeeder,
    ):
        """Test pagination des entrées d'humeur"""
        # Créer 15 entrées de test
        test_data_seeder.create_realistic_mood_data(test_user_with_consent.id, 15)

        # Test première page
        response = client.get(
            "/moods/?skip=0&limit=10", headers=auth_headers_with_consent
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

        # Test deuxième page
        response = client.get(
            "/moods/?skip=10&limit=10", headers=auth_headers_with_consent
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_mood_entries_by_date_range(
        self,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test filtrage par plage de dates"""
        start_date = (datetime.now().date() - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = datetime.now().date().strftime("%Y-%m-%d")

        response = client.get(
            f"/moods/?start_date={start_date}&end_date={end_date}",
            headers=auth_headers_with_consent,
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier que toutes les entrées sont dans la plage
        for entry in data:
            assert start_date <= entry["date"] <= end_date

    def test_get_mood_entries_empty_result(
        self, auth_headers_with_consent: Dict[str, str]
    ):
        """Test résultat vide quand pas d'entrées"""
        response = client.get("/moods/", headers=auth_headers_with_consent)

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_mood_entries_unauthorized(self):
        """Test accès non autorisé"""
        response = client.get("/moods/")
        assert response.status_code == 401


class TestMoodStats:
    """Tests pour les statistiques d'humeur"""

    def test_get_mood_stats_success(
        self,
        mood_entries_week: list,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test récupération des statistiques"""
        response = client.get("/moods/stats", headers=auth_headers_with_consent)

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure
        assert "average_mood" in data
        assert "average_stress" in data
        assert "average_sleep" in data
        assert "total_entries" in data
        assert "period_start" in data
        assert "period_end" in data

        # Vérifier les valeurs
        assert isinstance(data["average_mood"], float)
        assert data["total_entries"] == len(mood_entries_week)

        # Vérifier les dates
        assert datetime.strptime(data["period_start"], "%Y-%m-%d")
        assert datetime.strptime(data["period_end"], "%Y-%m-%d")

    def test_get_mood_stats_custom_period(
        self,
        test_user_with_consent: User,
        auth_headers_with_consent: Dict[str, str],
        test_data_seeder: TestDataSeeder,
    ):
        """Test statistiques pour une période personnalisée"""
        # Créer des données avec tendance
        test_data_seeder.create_mood_trend_data(test_user_with_consent.id, "improving")

        response = client.get("/moods/stats?days=14", headers=auth_headers_with_consent)

        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 14

    def test_get_mood_stats_no_data(self, auth_headers_with_consent: Dict[str, str]):
        """Test statistiques sans données"""
        response = client.get("/moods/stats", headers=auth_headers_with_consent)

        assert response.status_code == 200
        data = response.json()

        assert data["average_mood"] == 0
        assert data["total_entries"] == 0


class TestMoodCRUD:
    """Tests pour les opérations CRUD sur les entrées d'humeur"""

    def test_get_specific_mood_entry(
        self,
        mood_entries_week: list,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test récupération d'une entrée spécifique"""
        mood_entry = mood_entries_week[0]

        response = client.get(
            f"/moods/{mood_entry.id}", headers=auth_headers_with_consent
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == mood_entry.id
        assert data["mood"] == mood_entry.mood
        assert data["date"] == mood_entry.date

    def test_update_mood_entry(
        self,
        db: Session,
        mood_entries_week: list,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test mise à jour d'une entrée d'humeur"""
        mood_entry = mood_entries_week[0]
        update_data = {"mood": 5, "notes": "Updated notes"}

        response = client.put(
            f"/moods/{mood_entry.id}",
            json=update_data,
            headers=auth_headers_with_consent,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["mood"] == 5
        assert data["notes"] == "Updated notes"

        # Vérifier en base
        db.refresh(mood_entry)
        assert mood_entry.mood == 5
        assert mood_entry.notes == "Updated notes"

    def test_delete_mood_entry(
        self,
        db: Session,
        mood_entries_week: list,
        auth_headers_with_consent: Dict[str, str],
    ):
        """Test suppression d'une entrée d'humeur"""
        mood_entry = mood_entries_week[0]
        mood_id = mood_entry.id

        response = client.delete(f"/moods/{mood_id}", headers=auth_headers_with_consent)

        assert response.status_code == 204

        # Vérifier suppression en base
        deleted_entry = db.query(MoodEntry).filter(MoodEntry.id == mood_id).first()
        assert deleted_entry is None

    def test_access_other_user_mood_entry(
        self,
        mood_entries_week: list,
        auth_headers_other_user: Dict[str, str],
    ):
        """Test accès interdit aux entrées d'autres utilisateurs"""
        mood_entry = mood_entries_week[0]

        response = client.get(
            f"/moods/{mood_entry.id}", headers=auth_headers_other_user
        )

        assert response.status_code == 403
        assert "Accès non autorisé" in response.json()["detail"]
