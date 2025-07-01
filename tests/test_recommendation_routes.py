import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.models.user import User
from app.db.models.mood_entry import MoodEntry


class TestRecommendationRoutes:
    """Tests d'intégration pour les routes de recommandations"""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI"""
        return TestClient(app)

    @pytest.fixture
    def test_user_low_mood(self, db: Session, test_data_seeder):
        """Utilisateur avec entrée d'humeur basse"""
        user = test_data_seeder.create_test_user(
            email="lowmood@test.com",
            consent=True
        )
        
        # Créer une entrée d'humeur très basse
        mood_entry = test_data_seeder.create_test_mood_entry(
            user_id=user.id,
            mood=1,  # Très triste
            stress_level=4,
            notes="Je me sens très mal",
            date="2024-01-15"
        )
        
        return {"user": user, "mood_entry": mood_entry}

    def test_generate_recommendations_for_low_mood(
        self, 
        client: TestClient, 
        test_user_low_mood, 
        auth_headers
    ):
        """Test API de génération de recommandations pour humeur basse"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        # Générer des recommandations
        response = client.post(
            "/recommendations/generate",
            json={
                "mood_id": str(user_data["mood_entry"].id),  # Convert to string
                "time_available": 30
            },
            headers=headers
        )
        
        assert response.status_code == 201
        recommendations = response.json()
        
        # Vérifications
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert len(recommendations) <= 3
        
        for reco in recommendations:
            assert "id" in reco
            assert "suggested_activity" in reco
            assert "recommendation_type" in reco
            assert reco["recommendation_type"] == "mood_based"
            assert "confidence_score" in reco
            assert isinstance(reco["confidence_score"], (int, float))

    def test_generate_recommendations_with_direct_mood_level(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers
    ):
        """Test génération avec niveau d'humeur direct"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        response = client.post(
            "/recommendations/generate",
            json={
                "mood_level": 1,  # Très triste
                "time_available": 15
            },
            headers=headers
        )
        
        assert response.status_code == 201
        recommendations = response.json()
        assert len(recommendations) > 0

    def test_get_user_recommendations(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers
    ):
        """Test récupération des recommandations utilisateur"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        # D'abord générer quelques recommandations
        client.post(
            "/recommendations/generate",
            json={"mood_level": 1, "time_available": 30},
            headers=headers
        )
        
        # Récupérer la liste
        response = client.get("/recommendations/", headers=headers)
        
        assert response.status_code == 200
        recommendations = response.json()
        assert isinstance(recommendations, list)

    def test_update_recommendation_feedback(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers
    ):
        """Test mise à jour du feedback de recommandation"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        # Générer une recommandation
        gen_response = client.post(
            "/recommendations/generate",
            json={"mood_level": 1},
            headers=headers
        )
        recommendations = gen_response.json()
        reco_id = recommendations[0]["id"]
        
        # Mettre à jour le feedback
        feedback_response = client.put(
            f"/recommendations/{reco_id}/feedback",
            json={"was_helpful": True},
            headers=headers
        )
        
        assert feedback_response.status_code == 200
        updated_reco = feedback_response.json()
        assert updated_reco["was_helpful"] is True

    def test_get_recommendation_stats(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers
    ):
        """Test statistiques de recommandations"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        # Générer et évaluer quelques recommandations
        gen_response = client.post(
            "/recommendations/generate",
            json={"mood_level": 1},
            headers=headers
        )
        recommendations = gen_response.json()
        
        # Ajouter du feedback
        for i, reco in enumerate(recommendations[:2]):
            client.put(
                f"/recommendations/{reco['id']}/feedback",
                json={"was_helpful": i == 0},  # Premier utile, deuxième pas utile
                headers=headers
            )
        
        # Récupérer les stats
        stats_response = client.get("/recommendations/stats", headers=headers)
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert "total_recommendations" in stats
        assert "helpful_count" in stats
        assert "helpfulness_rate" in stats
        assert stats["total_recommendations"] >= len(recommendations)

    def test_generate_recommendations_no_consent(
        self,
        client: TestClient,
        db: Session,
        test_data_seeder,
        auth_headers
    ):
        """Test rejet pour utilisateur sans consentement"""
        # Utilisateur sans consentement
        user = test_data_seeder.create_test_user(
            email="noconsent@test.com",
            consent=False
        )
        headers = auth_headers(user)
        
        response = client.post(
            "/recommendations/generate",
            json={"mood_level": 1},
            headers=headers
        )
        
        assert response.status_code == 403
        assert "Consentement requis" in response.json()["detail"]

    def test_get_pending_feedback_recommendations(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers
    ):
        """Test récupération des recommandations en attente de feedback"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        # Générer des recommandations
        client.post(
            "/recommendations/generate",
            json={"mood_level": 1},
            headers=headers
        )
        
        # Récupérer celles en attente de feedback
        response = client.get("/recommendations/pending-feedback", headers=headers)
        
        assert response.status_code == 200
        pending = response.json()
        assert isinstance(pending, list)
        
        # Toutes devraient être en attente de feedback
        for reco in pending:
            assert reco["was_helpful"] is None

    @pytest.mark.parametrize("mood_level,time_available", [
        (1, 10),   # Très triste, peu de temps
        (1, 30),   # Très triste, temps normal
        (1, 60),   # Très triste, beaucoup de temps
        (2, 15),   # Triste, peu de temps
        (2, 45),   # Triste, temps normal
    ])
    def test_generate_recommendations_various_low_mood_scenarios(
        self,
        client: TestClient,
        test_user_low_mood,
        auth_headers,
        mood_level,
        time_available
    ):
        """Test génération pour différents scénarios d'humeur basse"""
        user_data = test_user_low_mood
        headers = auth_headers(user_data["user"])
        
        response = client.post(
            "/recommendations/generate",
            json={
                "mood_level": mood_level,
                "time_available": time_available
            },
            headers=headers
        )
        
        assert response.status_code == 201
        recommendations = response.json()
        assert len(recommendations) > 0
        
        # Vérifier que les recommandations respectent le temps disponible
        # (Cette vérification nécessiterait d'exposer plus de détails dans l'API)
        for reco in recommendations:
            assert reco["confidence_score"] > 0.5  # Score minimum attendu
