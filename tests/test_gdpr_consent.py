import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.main import app
from app.db.models.user import User
from app.db.models.mood_entry import MoodEntry
from app.schemas.mood_dto import MoodEntryCreate
from tests.utils.test_data_seeder import TestDataSeeder

client = TestClient(app)


class TestGDPRConsent:
    """Tests pour la validation du consentement RGPD"""
    
    def test_mood_creation_rejected_without_consent(
        self,
        db: Session,
        test_user_no_consent: User,
        test_data_seeder: TestDataSeeder
    ):
        """Test: création d'humeur rejetée sans consentement RGPD"""
        # Créer un token pour l'utilisateur sans consentement
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": test_user_no_consent.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 4,
            "notes": "Test mood without consent",
            "activity": "Testing",
            "sleep_hours": 8.0,
            "stress_level": 2
        }
        
        # Tentative de création
        response = client.post("/moods/", json=mood_data, headers=headers)
        
        # Vérifications
        assert response.status_code == 403
        error_detail = response.json()["detail"]
        assert "Consentement requis" in error_detail
        assert "sauvegarder les données d'humeur" in error_detail
        
        # Vérifier qu'aucune entrée n'a été créée en base
        mood_count = db.query(MoodEntry).filter(
            MoodEntry.user_id == test_user_no_consent.id
        ).count()
        assert mood_count == 0

    def test_mood_creation_successful_with_consent(
        self,
        db: Session,
        test_user_with_consent: User
    ):
        """Test: création d'humeur réussie avec consentement RGPD"""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": test_user_with_consent.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 4,
            "notes": "Test mood with consent",
            "activity": "Testing",
            "sleep_hours": 8.0,
            "stress_level": 2
        }
        
        # Création réussie
        response = client.post("/moods/", json=mood_data, headers=headers)
        
        # Vérifications
        assert response.status_code == 201
        data = response.json()
        assert data["mood"] == 4
        assert data["notes"] == "Test mood with consent"
        assert data["collected"] == True  # Doit être True avec consentement
        
        # Vérifier en base de données
        mood_entry = db.query(MoodEntry).filter(
            MoodEntry.user_id == test_user_with_consent.id
        ).first()
        assert mood_entry is not None
        assert mood_entry.mood == 4

    def test_consent_flag_affects_collected_status(
        self,
        db: Session,
        test_user_with_consent: User,
        test_user_no_consent: User
    ):
        """Test: le flag 'collected' reflète le statut de consentement"""
        from app.core.security import create_access_token
        
        # Utilisateur avec consentement
        token_consent = create_access_token(data={"sub": test_user_with_consent.email})
        headers_consent = {"Authorization": f"Bearer {token_consent}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 3
        }
        
        response = client.post("/moods/", json=mood_data, headers=headers_consent)
        assert response.status_code == 201
        data = response.json()
        assert data["collected"] == True
        
        # Vérifier que l'utilisateur sans consentement ne peut pas créer
        token_no_consent = create_access_token(data={"sub": test_user_no_consent.email})
        headers_no_consent = {"Authorization": f"Bearer {token_no_consent}"}
        
        mood_data_no_consent = {
            "date": (datetime.now().date()).strftime('%Y-%m-%d'),
            "mood": 2
        }
        
        response = client.post("/moods/", json=mood_data_no_consent, headers=headers_no_consent)
        assert response.status_code == 403

    def test_user_consent_status_verification(
        self,
        test_user_with_consent: User,
        test_user_no_consent: User
    ):
        """Test: vérification du statut de consentement des utilisateurs"""
        # Vérifier les utilisateurs de test
        assert test_user_with_consent.consent == True
        assert test_user_no_consent.consent == False

    def test_multiple_users_consent_isolation(
        self,
        db: Session,
        test_data_seeder: TestDataSeeder
    ):
        """Test: isolation du consentement entre utilisateurs"""
        from app.core.security import create_access_token
        
        # Créer plusieurs utilisateurs avec différents statuts de consentement
        user_consent_1 = test_data_seeder.create_test_user(
            email="consent1@test.com", consent=True
        )
        user_consent_2 = test_data_seeder.create_test_user(
            email="consent2@test.com", consent=True
        )
        user_no_consent = test_data_seeder.create_test_user(
            email="noconsent2@test.com", consent=False
        )
        
        # Test création pour utilisateurs avec consentement
        for user in [user_consent_1, user_consent_2]:
            token = create_access_token(data={"sub": user.email})
            headers = {"Authorization": f"Bearer {token}"}
            
            mood_data = {
                "date": datetime.now().date().strftime('%Y-%m-%d'),
                "mood": 4
            }
            
            response = client.post("/moods/", json=mood_data, headers=headers)
            assert response.status_code == 201
        
        # Test rejet pour utilisateur sans consentement
        token_no_consent = create_access_token(data={"sub": user_no_consent.email})
        headers_no_consent = {"Authorization": f"Bearer {token_no_consent}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 3
        }
        
        response = client.post("/moods/", json=mood_data, headers=headers_no_consent)
        assert response.status_code == 403
        
        # Vérifier le nombre d'entrées créées
        total_entries = db.query(MoodEntry).count()
        assert total_entries == 2  # Seulement les utilisateurs avec consentement

    def test_gdpr_error_message_clarity(
        self,
        test_user_no_consent: User
    ):
        """Test: clarté du message d'erreur RGPD"""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": test_user_no_consent.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 3
        }
        
        response = client.post("/moods/", json=mood_data, headers=headers)
        
        assert response.status_code == 403
        error_response = response.json()
        
        # Vérifier la structure de l'erreur
        assert "detail" in error_response
        
        # Vérifier que le message est explicite
        detail = error_response["detail"]
        assert "Consentement" in detail
        assert "requis" in detail
        assert "données d'humeur" in detail

    def test_service_layer_consent_validation(
        self,
        db: Session,
        test_user_no_consent: User
    ):
        """Test: validation du consentement au niveau service"""
        from app.repositories.mood_repository import MoodRepository
        from app.services.mood_service import MoodService
        from app.schemas.mood import MoodEntryCreate
        from fastapi import HTTPException
        
        # Créer le service
        mood_repository = MoodRepository(db)
        mood_service = MoodService(mood_repository)
        
        # Données de test
        mood_data = MoodEntryCreate(
            date=datetime.now().date().strftime('%Y-%m-%d'),
            mood=3
        )
        
        # Test que le service rejette sans consentement
        with pytest.raises(HTTPException) as exc_info:
            mood_service.create_mood_entry(test_user_no_consent, mood_data)
        
        assert exc_info.value.status_code == 403
        assert "Consentement requis" in str(exc_info.value.detail)


class TestGDPRComplianceFeatures:
    """Tests pour les fonctionnalités de conformité RGPD"""
    
    def test_user_can_access_own_data_regardless_of_consent(
        self,
        db: Session,
        test_user_no_consent: User,
        test_data_seeder: TestDataSeeder
    ):
        """Test: utilisateur peut accéder à ses données même sans consentement actuel"""
        # Créer manuellement une entrée d'humeur (comme si créée avant retrait du consentement)
        mood_entry = MoodEntry(
            user_id=test_user_no_consent.id,
            date=datetime.now().date().strftime('%Y-%m-%d'),
            mood=3,
            collected=False  # Pas collectée dans le cloud
        )
        db.add(mood_entry)
        db.commit()
        
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": test_user_no_consent.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        # L'utilisateur doit pouvoir lire ses données existantes
        response = client.get("/moods/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["collected"] == False

    def test_collected_flag_reflects_consent_status(
        self,
        db: Session,
        test_user_with_consent: User
    ):
        """Test: le flag 'collected' reflète correctement le statut de consentement"""
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": test_user_with_consent.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        mood_data = {
            "date": datetime.now().date().strftime('%Y-%m-%d'),
            "mood": 4
        }
        
        response = client.post("/moods/", json=mood_data, headers=headers)
        assert response.status_code == 201
        
        data = response.json()
        # Avec consentement, collected doit être True
        assert data["collected"] == True
        
        # Vérifier en base de données
        mood_entry = db.query(MoodEntry).filter(
            MoodEntry.user_id == test_user_with_consent.id
        ).first()
        assert mood_entry.collected == True
