from typing import Dict
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app.main import app
from app.schemas.stats_dto import UserOverallStats, WeeklyMoodTrend, MoodDistribution


class TestStatsRoutes:
    """Tests pour les routes de statistiques"""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI"""
        return TestClient(app)

    @pytest.fixture
    def mock_user_token(self):
        """Mock d'un token utilisateur valide"""
        with patch('app.core.security.get_current_user') as mock_get_user:
            mock_user = Mock()
            mock_user.id = "user-123"
            mock_user.consent = True
            mock_get_user.return_value = mock_user
            yield mock_user

    def test_get_stats_overview_7_days(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test de l'endpoint overview avec 7 jours"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            # Mock du service
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            # Mock des données de retour
            mock_service_instance.get_user_overall_stats.return_value = UserOverallStats(
                period_start="2024-01-09",
                period_end="2024-01-15",
                mood_entries_count=6,
                average_mood=3.5,
                average_sleep=7.2,
                average_stress=2.8,
                chat_messages_count=15,
                recommendations_received=8,
                recommendations_helpful=6,
                wellness_score=75.5,
                insights=["Bonne régularité dans le suivi", "Corrélation positive sommeil-humeur"]
            )
            
            mock_service_instance.get_weekly_mood_trends.return_value = [
                WeeklyMoodTrend(
                    week_start="2024-01-09",
                    week_end="2024-01-15",
                    entries_count=6,
                    average_mood=3.5,
                    average_stress=2.8,
                    average_sleep=7.2,
                    mood_trend="improving"
                )
            ]
            
            mock_service_instance.get_mood_distribution.return_value = MoodDistribution(
                total_entries=6,
                mood_1_count=0,
                mood_2_count=1,
                mood_3_count=2,
                mood_4_count=2,
                mood_5_count=1,
                mood_1_percentage=0.0,
                mood_2_percentage=16.7,
                mood_3_percentage=33.3,
                mood_4_percentage=33.3,
                mood_5_percentage=16.7,
                most_common_mood=3
            )
            
            mock_service_instance.get_activity_effectiveness.return_value = []
            mock_service_instance.get_daily_mood_entries.return_value = []
            mock_service_instance.get_period_comparison.return_value = None
            
            # Requête
            response = client.get("/stats/overview?days=7", headers=auth_headers_with_consent)
            
            # Vérifications
            assert response.status_code == 200
            data = response.json()
            
            assert "user_stats" in data
            assert "weekly_trends" in data
            assert "mood_distribution" in data
            assert "daily_entries" in data
            
            # Vérifier les données utilisateur
            user_stats = data["user_stats"]
            assert user_stats["mood_entries_count"] == 6
            assert user_stats["average_mood"] == 3.5
            assert user_stats["wellness_score"] == 75.5
            assert len(user_stats["insights"]) == 2
            
            # Vérifier que le service a été appelé avec les bons paramètres
            mock_service_instance.get_user_overall_stats.assert_called_once_with("user-123", 7)

    def test_get_weekly_trends_4_weeks(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test de l'endpoint weekly trends"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            # Mock de 4 semaines de données
            mock_trends = []
            for i in range(4):
                start_date = datetime.now().date() - timedelta(days=(4-i-1)*7 + 6)
                end_date = start_date + timedelta(days=6)
                
                trend = WeeklyMoodTrend(
                    week_start=start_date.strftime("%Y-%m-%d"),
                    week_end=end_date.strftime("%Y-%m-%d"),
                    entries_count=5 + i,  # Progression
                    average_mood=2.5 + i * 0.3,  # Amélioration graduelle
                    average_stress=4.0 - i * 0.2,  # Diminution du stress
                    average_sleep=7.0 + i * 0.1,
                    mood_trend="improving" if i >= 2 else "stable"
                )
                mock_trends.append(trend)
            
            mock_service_instance.get_weekly_mood_trends.return_value = mock_trends
            
            # Requête
            response = client.get("/stats/weekly?weeks=4", headers=auth_headers_with_consent)
            
            # Vérifications
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 4
            
            # Vérifier l'ordre chronologique (plus ancien en premier)
            for i in range(len(data) - 1):
                current_end = datetime.strptime(data[i]["week_end"], "%Y-%m-%d").date()
                next_start = datetime.strptime(data[i+1]["week_start"], "%Y-%m-%d").date()
                assert current_end < next_start
            
            # Vérifier la progression des données
            assert data[0]["entries_count"] == 5
            assert data[-1]["entries_count"] == 8
            assert data[-1]["average_mood"] > data[0]["average_mood"]

    def test_get_mood_distribution_7_days(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test de l'endpoint distribution d'humeur"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            mock_service_instance.get_mood_distribution.return_value = MoodDistribution(
                total_entries=14,  # 2 semaines de données quotidiennes
                mood_1_count=1,
                mood_2_count=2,
                mood_3_count=5,
                mood_4_count=4,
                mood_5_count=2,
                mood_1_percentage=7.1,
                mood_2_percentage=14.3,
                mood_3_percentage=35.7,
                mood_4_percentage=28.6,
                mood_5_percentage=14.3,
                most_common_mood=3
            )
            
            # Requête
            response = client.get("/stats/mood-distribution?days=14", headers=auth_headers_with_consent)
            
            # Vérifications
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_entries"] == 14
            assert data["most_common_mood"] == 3
            
            # Vérifier que les pourcentages somment à 100%
            total_percentage = (
                data["mood_1_percentage"] + 
                data["mood_2_percentage"] + 
                data["mood_3_percentage"] + 
                data["mood_4_percentage"] + 
                data["mood_5_percentage"]
            )
            assert abs(total_percentage - 100.0) < 0.1  # Tolérance pour les arrondis

    def test_get_overall_stats_various_periods(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test de l'endpoint overall stats avec différentes périodes"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            def mock_get_stats(user_id, days):
                return UserOverallStats(
                    period_start=(datetime.now().date() - timedelta(days=days-1)).strftime("%Y-%m-%d"),
                    period_end=datetime.now().date().strftime("%Y-%m-%d"),
                    mood_entries_count=days // 2,  # Simulation: une entrée tous les 2 jours
                    average_mood=3.0 + (days / 30),  # Plus de données = meilleure humeur
                    average_sleep=7.0,
                    average_stress=3.0,
                    chat_messages_count=days,
                    recommendations_received=days // 3,
                    recommendations_helpful=days // 4,
                    wellness_score=50.0 + (days / 10),
                    insights=[]
                )
            
            mock_service_instance.get_user_overall_stats.side_effect = mock_get_stats
            
            # Test différentes périodes
            periods = [7, 14, 30, 90]
            for days in periods:
                response = client.get(f"/stats/overall?days={days}", headers=auth_headers_with_consent)
                assert response.status_code == 200
                
                data = response.json()
                assert data["mood_entries_count"] == days // 2
                assert data["wellness_score"] == 50.0 + (days / 10)
                
                # Vérifier que le service a été appelé avec les bons paramètres
                mock_service_instance.get_user_overall_stats.assert_called_with("user-123", days)

    def test_stats_endpoints_validation(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test de validation des paramètres des endpoints"""
        
        # Test avec des paramètres invalides
        invalid_requests = [
            "/stats/overall?days=0",      # Trop petit
            "/stats/overall?days=400",    # Trop grand
            "/stats/weekly?weeks=0",      # Trop petit
            "/stats/weekly?weeks=15",     # Trop grand
            "/stats/mood-distribution?days=5"  # Trop petit pour distribution
        ]
        
        for url in invalid_requests:
            response = client.get(url, headers=auth_headers_with_consent)
            assert response.status_code == 422  # Validation error

    def test_stats_empty_data_response(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test des réponses avec données vides"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            # Données vides
            mock_service_instance.get_user_overall_stats.return_value = UserOverallStats(
                period_start="2024-01-09",
                period_end="2024-01-15",
                mood_entries_count=0,
                average_mood=0.0,
                average_sleep=None,
                average_stress=None,
                chat_messages_count=0,
                recommendations_received=0,
                recommendations_helpful=0,
                wellness_score=50.0,  # Score par défaut
                insights=["Commencez à enregistrer votre humeur pour obtenir des insights"]
            )
            
            response = client.get("/stats/overall?days=7", headers=auth_headers_with_consent)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["mood_entries_count"] == 0
            assert data["wellness_score"] == 50.0
            assert len(data["insights"]) >= 1

    def test_unauthorized_access_stats(self, client):
        """Test d'accès non autorisé aux statistiques"""
        
        # Sans token
        response = client.get("/stats/overview")
        assert response.status_code == 401
        
        response = client.get("/stats/weekly")
        assert response.status_code == 401
        
        response = client.get("/stats/mood-distribution")
        assert response.status_code == 401

    def test_stats_performance_with_large_dataset(self, client, auth_headers_with_consent: Dict[str, str]):
        """Test des performances avec un large dataset simulé"""
        
        with patch('app.services.stats_service.StatsService') as mock_stats_service:
            mock_service_instance = Mock()
            mock_stats_service.return_value = mock_service_instance
            
            # Simuler un dataset important (365 jours)
            mock_service_instance.get_user_overall_stats.return_value = UserOverallStats(
                period_start="2024-07-01",
                period_end="2025-07-01",
                mood_entries_count=300,  # Presque quotidien
                average_mood=3.2,
                average_sleep=7.1,
                average_stress=2.9,
                chat_messages_count=450,
                recommendations_received=150,
                recommendations_helpful=120,
                wellness_score=82.5,
                insights=["Excellent suivi régulier", "Tendance d'amélioration", "Bon équilibre"]
            )
            
            # La requête devrait toujours être rapide
            import time
            start_time = time.time()
            
            response = client.get("/stats/overall?days=365", headers=auth_headers_with_consent)
            
            end_time = time.time()
            request_time = end_time - start_time

            assert response.status_code == 200
            assert request_time < 1.0  # Moins d'une seconde
            
            data = response.json()
            print(data)  # Pour débogage
            assert data["mood_entries_count"] == 300
            assert data["wellness_score"] == 82.5
