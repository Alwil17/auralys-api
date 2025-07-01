import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from sqlalchemy.orm import Session

from app.services.stats_service import StatsService
from app.repositories.mood_repository import MoodRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.stats_dto import UserOverallStats, WeeklyMoodTrend, MoodDistribution


class TestStatsService:
    """Tests pour le service de statistiques"""

    @pytest.fixture
    def mock_repositories(self):
        """Mocks des repositories"""
        mood_repo = Mock(spec=MoodRepository)
        chat_repo = Mock(spec=ChatRepository)
        reco_repo = Mock(spec=RecommendationRepository)
        return mood_repo, chat_repo, reco_repo

    @pytest.fixture
    def stats_service(self, mock_repositories):
        """Service de stats avec mocks"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Mock de la session DB
        db_session = Mock(spec=Session)

        service = StatsService(db_session)
        service.mood_repository = mood_repo
        service.chat_repository = chat_repo
        service.recommendation_repository = reco_repo

        return service

    def test_get_user_overall_stats_7_days(self, stats_service, mock_repositories):
        """Test des statistiques générales sur 7 jours"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Mock des données de retour
        mood_repo.get_user_mood_stats.return_value = {
            "total_entries": 6,
            "average_mood": 3.5,
            "average_sleep": 7.2,
            "average_stress": 2.8,
        }

        chat_repo.get_chat_stats.return_value = {
            "messages_user": 15,
            "messages_bot": 15,
            "total_messages": 30,
        }

        reco_repo.get_recommendation_stats.return_value = {
            "total_recommendations": 8,
            "helpful_count": 6,
            "not_helpful_count": 2,
        }

        # Mock pour les insights
        mood_repo.get_user_mood_entries_by_date_range.return_value = [
            Mock(sleep_hours=8.0, mood=4, stress_level=2),
            Mock(sleep_hours=7.0, mood=3, stress_level=3),
            Mock(sleep_hours=8.5, mood=4, stress_level=2),
        ]

        # Exécuter
        result = stats_service.get_user_overall_stats("user-123", days=7)

        # Vérifications
        assert isinstance(result, UserOverallStats)
        assert result.mood_entries_count == 6
        assert result.average_mood == 3.5
        assert result.average_sleep == 7.2
        assert result.average_stress == 2.8
        assert result.chat_messages_count == 15
        assert result.recommendations_received == 8
        assert result.recommendations_helpful == 6
        assert 0 <= result.wellness_score <= 100
        assert isinstance(result.insights, list)

        # Vérifier les appels aux repositories
        mood_repo.get_user_mood_stats.assert_called_once_with("user-123", 7)
        chat_repo.get_chat_stats.assert_called_once_with("user-123", 7)
        reco_repo.get_recommendation_stats.assert_called_once_with("user-123", 7)

    def test_get_weekly_mood_trends_4_weeks(self, stats_service, mock_repositories):
        """Test des tendances hebdomadaires sur 4 semaines"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Simuler des entrées d'humeur pour différentes semaines
        def mock_get_entries_by_date_range(user_id, start_date, end_date):
            # Parse les dates pour déterminer quelle semaine
            start = datetime.strptime(start_date, "%Y-%m-%d").date()

            # Simuler différentes données selon la semaine
            if start >= datetime.now().date() - timedelta(days=6):
                # Semaine actuelle - bonnes données
                return [
                    Mock(mood=4, stress_level=2, sleep_hours=8.0),
                    Mock(mood=3, stress_level=3, sleep_hours=7.5),
                    Mock(mood=5, stress_level=1, sleep_hours=8.5),
                ]
            elif start >= datetime.now().date() - timedelta(days=13):
                # Semaine précédente - données moyennes
                return [
                    Mock(mood=3, stress_level=3, sleep_hours=7.0),
                    Mock(mood=2, stress_level=4, sleep_hours=6.5),
                ]
            else:
                # Semaines plus anciennes - moins de données
                return [Mock(mood=2, stress_level=4, sleep_hours=6.0)]

        mood_repo.get_user_mood_entries_by_date_range.side_effect = (
            mock_get_entries_by_date_range
        )

        # Exécuter
        trends = stats_service.get_weekly_mood_trends("user-123", weeks=4)

        # Vérifications
        assert len(trends) == 4
        assert all(isinstance(trend, WeeklyMoodTrend) for trend in trends)

        # La première entrée devrait être la plus ancienne
        oldest_trend = trends[0]
        newest_trend = trends[-1]

        assert oldest_trend.entries_count >= 0
        assert newest_trend.entries_count >= 0

        # Vérifier que les dates sont dans l'ordre chronologique
        for i in range(len(trends) - 1):
            current_end = datetime.strptime(trends[i].week_end, "%Y-%m-%d").date()
            next_start = datetime.strptime(trends[i + 1].week_start, "%Y-%m-%d").date()
            assert current_end < next_start

        # Vérifier les calculs de tendance
        assert newest_trend.mood_trend in ["improving", "declining", "stable"]

    def test_get_mood_distribution_7_days(self, stats_service, mock_repositories):
        """Test de la distribution des humeurs sur 7 jours"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Simuler des entrées avec différents niveaux d'humeur
        mock_entries = [
            Mock(mood=1),  # 1 occurrence
            Mock(mood=2),
            Mock(mood=2),  # 2 occurrences
            Mock(mood=3),
            Mock(mood=3),
            Mock(mood=3),  # 3 occurrences
            Mock(mood=4),  # 1 occurrence
            Mock(mood=5),  # 1 occurrence
        ]

        mood_repo.get_user_mood_entries_by_date_range.return_value = mock_entries

        # Exécuter
        distribution = stats_service.get_mood_distribution("user-123", days=7)

        # Vérifications
        assert isinstance(distribution, MoodDistribution)
        assert distribution.total_entries == 8
        assert distribution.mood_1_count == 1
        assert distribution.mood_2_count == 2
        assert distribution.mood_3_count == 3
        assert distribution.mood_4_count == 1
        assert distribution.mood_5_count == 1

        # Vérifier les pourcentages
        assert distribution.mood_1_percentage == 12.5  # 1/8 * 100
        assert distribution.mood_2_percentage == 25.0  # 2/8 * 100
        assert distribution.mood_3_percentage == 37.5  # 3/8 * 100

        # L'humeur la plus commune devrait être 3
        assert distribution.most_common_mood == 3

    def test_calculate_wellness_score_various_scenarios(self, stats_service):
        """Test du calcul du score de bien-être dans différents scénarios"""

        # Scénario 1: Excellentes données
        mood_stats = {"average_mood": 4.5, "total_entries": 25}
        chat_stats = {"messages_user": 15}
        reco_stats = {"helpfulness_rate": 0.8}

        score = stats_service._calculate_wellness_score(
            mood_stats, chat_stats, reco_stats
        )
        assert 70 <= score <= 100  # Devrait être élevé

        # Scénario 2: Données moyennes
        mood_stats = {"average_mood": 3.0, "total_entries": 10}
        chat_stats = {"messages_user": 5}
        reco_stats = {"helpfulness_rate": 0.5}

        score = stats_service._calculate_wellness_score(
            mood_stats, chat_stats, reco_stats
        )
        assert 40 <= score <= 70  # Devrait être moyen

        # Scénario 3: Données faibles
        mood_stats = {"average_mood": 2.0, "total_entries": 3}
        chat_stats = {"messages_user": 1}
        reco_stats = {"helpfulness_rate": 0.2}

        score = stats_service._calculate_wellness_score(
            mood_stats, chat_stats, reco_stats
        )
        assert 0 <= score <= 50  # Devrait être bas

    def test_calculate_trend_different_patterns(self, stats_service):
        """Test du calcul de tendance avec différents patterns"""

        # Tendance croissante
        improving_moods = [2, 2, 3, 3, 4, 4, 5]
        trend = stats_service._calculate_trend(improving_moods)
        assert trend == "improving"

        # Tendance décroissante
        declining_moods = [5, 4, 4, 3, 3, 2, 2]
        trend = stats_service._calculate_trend(declining_moods)
        assert trend == "declining"

        # Tendance stable
        stable_moods = [3, 3, 3, 3, 3, 3, 3]
        trend = stats_service._calculate_trend(stable_moods)
        assert trend == "stable"

        # Données insuffisantes
        single_mood = [3]
        trend = stats_service._calculate_trend(single_mood)
        assert trend == "stable"

    def test_generate_wellness_insights_various_scenarios(
        self, stats_service, mock_repositories
    ):
        """Test de génération d'insights dans différents scénarios"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Scénario 1: Utilisateur régulier avec bon sommeil
        regular_user_entries = []
        for i in range(6):  # 6 entrées sur 7 jours = régulier
            entry = Mock()
            entry.sleep_hours = (
                8.0 if i % 2 == 0 else 6.0
            )  # Alternance bon/mauvais sommeil
            entry.mood = 4 if i % 2 == 0 else 2  # Humeur corrélée au sommeil
            entry.stress_level = 2
            regular_user_entries.append(entry)

        mood_repo.get_user_mood_entries_by_date_range.return_value = (
            regular_user_entries
        )

        insights = stats_service._generate_wellness_insights("user-123", 7)

        assert isinstance(insights, list)
        assert len(insights) <= 3  # Maximum 3 insights selon le service

        # Vérifier qu'on a des insights pertinents
        insights_text = " ".join(insights).lower()
        assert any(
            keyword in insights_text for keyword in ["régulier", "données", "suivi"]
        )

        # Scénario 2: Nouvel utilisateur sans données
        mood_repo.get_user_mood_entries_by_date_range.return_value = []

        insights = stats_service._generate_wellness_insights("user-123", 7)

        assert isinstance(insights, list)
        assert len(insights) >= 1
        insights_text = " ".join(insights).lower()
        assert any(
            keyword in insights_text
            for keyword in ["commencez", "enregistrer", "données"]
        )

    def test_empty_data_handling(self, stats_service, mock_repositories):
        """Test de la gestion des données vides"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Tous les repositories retournent des données vides
        mood_repo.get_user_mood_stats.return_value = {
            "total_entries": 0,
            "average_mood": 0,
            "average_sleep": 0,
            "average_stress": 0,
        }

        chat_repo.get_chat_stats.return_value = {
            "messages_user": 0,
            "messages_bot": 0,
            "total_messages": 0,
        }

        reco_repo.get_recommendation_stats.return_value = {
            "total_recommendations": 0,
            "helpful_count": 0,
            "not_helpful_count": 0,
        }

        mood_repo.get_user_mood_entries_by_date_range.return_value = []

        # Test overall stats avec données vides
        result = stats_service.get_user_overall_stats("user-123", days=7)
        assert result.mood_entries_count == 0
        assert result.wellness_score >= 0  # Ne devrait pas planter

        # Test distribution avec données vides
        distribution = stats_service.get_mood_distribution("user-123", days=7)
        assert distribution.total_entries == 0
        assert distribution.most_common_mood is None

    def test_weekly_stats_date_calculations(self, stats_service, mock_repositories):
        """Test des calculs de dates pour les statistiques hebdomadaires"""
        mood_repo, chat_repo, reco_repo = mock_repositories

        # Mock des données pour différentes semaines
        def mock_get_entries_by_date_range(user_id, start_date, end_date):
            # Simuler des données selon la période
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            today = datetime.now().date()

            if start >= today - timedelta(days=6):
                # Semaine actuelle
                return [Mock(mood=4, stress_level=2, sleep_hours=8.0) for _ in range(3)]
            else:
                # Semaines précédentes
                return [Mock(mood=3, stress_level=3, sleep_hours=7.0) for _ in range(2)]

        mood_repo.get_user_mood_entries_by_date_range.side_effect = (
            mock_get_entries_by_date_range
        )

        # Exécuter
        trends = stats_service.get_weekly_mood_trends("user-123", weeks=2)

        # Vérifications
        assert isinstance(trends, list)
        assert len(trends) == 2

        # Vérifier que les dates font sens
        for trend in trends:
            assert isinstance(trend, WeeklyMoodTrend)
            start = datetime.strptime(trend.week_start, "%Y-%m-%d").date()
            end = datetime.strptime(trend.week_end, "%Y-%m-%d").date()

            # Une semaine = 6 jours d'écart (start to end inclusive)
            assert (end - start).days == 6

            # Vérifier que les données sont cohérentes
            assert trend.entries_count >= 0
            assert trend.mood_trend in ["improving", "declining", "stable"]
