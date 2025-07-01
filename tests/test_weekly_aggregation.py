import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.services.stats_service import StatsService


class TestWeeklyAggregation:
    """Tests spécifiques pour l'agrégation hebdomadaire"""

    @pytest.fixture
    def stats_service_with_real_data(self):
        """Service avec des données réalistes pour les tests d'agrégation"""
        service = StatsService(Mock())
        
        # Mock des repositories avec des méthodes qui simulent des vraies données
        service.mood_repository = Mock()
        service.chat_repository = Mock()
        service.recommendation_repository = Mock()
        
        return service

    def test_weekly_aggregation_exact_7_days(self, stats_service_with_real_data):
        """Test d'agrégation sur exactement 7 jours"""
        service = stats_service_with_real_data
        
        # Simuler des données pour une semaine complète
        # Base date pour la semaine (aujourd'hui -7 jours)
        datetime_now = datetime.today() - timedelta(days=6)
        base_date = datetime_now.date()
        weekly_entries = []
        
        for i in range(7):  # Lundi à Dimanche
            date = base_date + timedelta(days=i)
            entry = Mock()
            entry.mood = 3 + (i % 3)  # Variation d'humeur
            entry.stress_level = 2 + (i % 2)
            entry.sleep_hours = 7.0 + (i * 0.2)
            entry.date = date.strftime("%Y-%m-%d")
            weekly_entries.append(entry)
        
        def mock_get_entries(user_id, start_date, end_date):
            # Filtrer les entrées selon les dates demandées
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            return [
                entry for entry in weekly_entries 
                if start <= datetime.strptime(entry.date, "%Y-%m-%d").date() <= end
            ]
        
        service.mood_repository.get_user_mood_entries_by_date_range.side_effect = mock_get_entries
        
        # Tester l'agrégation hebdomadaire
        trends = service.get_weekly_mood_trends("user-123", weeks=1)
        
        assert len(trends) == 1
        week_trend = trends[0]
        
        # Vérifier que tous les 7 jours sont pris en compte
        assert week_trend.entries_count == 7
        
        # Vérifier les calculs de moyenne
        expected_avg_mood = sum(3 + (i % 3) for i in range(7)) / 7
        assert abs(week_trend.average_mood - expected_avg_mood) < 0.01
        
        expected_avg_stress = sum(2 + (i % 2) for i in range(7)) / 7
        assert abs(week_trend.average_stress - expected_avg_stress) < 0.01
        
        expected_avg_sleep = sum(7.0 + (i * 0.2) for i in range(7)) / 7
        assert abs(week_trend.average_sleep - expected_avg_sleep) < 0.01

    def test_weekly_aggregation_partial_weeks(self, stats_service_with_real_data):
        """Test d'agrégation avec des semaines partielles"""
        service = stats_service_with_real_data
        
        # Simuler des données partielles (seulement 3 jours dans la semaine)
        def mock_get_partial_entries(user_id, start_date, end_date):
            # Simuler que l'utilisateur n'a saisi que 3 jours
            datetime_now = datetime.today() - timedelta(days=6)
            base_date = datetime_now.date().strftime("%Y-%m-%d")
            print(f"Base date for partial entries: {base_date}")
            print(f"Start date for partial entries: {start_date}")
            if base_date in start_date:  # Semaine actuelle
                return [
                    Mock(mood=4, stress_level=2, sleep_hours=8.0),
                    Mock(mood=3, stress_level=3, sleep_hours=7.5),
                    Mock(mood=5, stress_level=1, sleep_hours=8.5)
                ]
            else:
                return []
        
        service.mood_repository.get_user_mood_entries_by_date_range.side_effect = mock_get_partial_entries
        
        trends = service.get_weekly_mood_trends("user-123", weeks=2)
        
        # Une semaine avec données, une sans
        current_week = trends[-1]  # La plus récente
        previous_week = trends[-2]
        
        assert current_week.entries_count == 3
        assert previous_week.entries_count == 0
        
        # Moyennes calculées uniquement sur les données disponibles
        assert current_week.average_mood == (4 + 3 + 5) / 3

    def test_weekly_trend_calculation_improving(self, stats_service_with_real_data):
        """Test de calcul de tendance d'amélioration"""
        service = stats_service_with_real_data
        
        # Série d'humeurs en amélioration
        improving_moods = [2, 2, 3, 3, 4, 4, 5]
        trend = service._calculate_trend(improving_moods)
        assert trend == "improving"
        
        # Amélioration légère
        slight_improvement = [3, 3, 3, 3, 4, 4, 4]
        trend = service._calculate_trend(slight_improvement)
        assert trend == "improving"

    def test_weekly_trend_calculation_declining(self, stats_service_with_real_data):
        """Test de calcul de tendance de déclin"""
        service = stats_service_with_real_data
        
        # Série d'humeurs en déclin
        declining_moods = [5, 4, 4, 3, 3, 2, 2]
        trend = service._calculate_trend(declining_moods)
        assert trend == "declining"
        
        # Déclin léger
        slight_decline = [4, 4, 4, 3, 3, 3, 3]
        trend = service._calculate_trend(slight_decline)
        assert trend == "declining"

    def test_weekly_trend_calculation_stable(self, stats_service_with_real_data):
        """Test de calcul de tendance stable"""
        service = stats_service_with_real_data
        
        # Série stable
        stable_moods = [3, 3, 3, 3, 3, 3, 3]
        trend = service._calculate_trend(stable_moods)
        assert trend == "stable"
        
        # Légères fluctuations mais stable globalement
        fluctuating_stable = [3, 4, 3, 3, 4, 3, 3]
        trend = service._calculate_trend(fluctuating_stable)
        assert trend == "stable"

    def test_weekly_aggregation_weekend_vs_weekday_patterns(self, stats_service_with_real_data):
        """Test de détection de patterns week-end vs semaine"""
        service = stats_service_with_real_data
        
        # Simuler des données avec pattern week-end/semaine
        datetime_now = datetime.today() - timedelta(days=6)
        base_date = datetime_now.date()
        weekly_entries = []
        
        for i in range(7):
            date = base_date + timedelta(days=i)
            entry = Mock()
            
            # Week-end (samedi=5, dimanche=6) = humeur plus élevée
            if i >= 5:  # Week-end
                entry.mood = 4
                entry.stress_level = 1
                entry.sleep_hours = 9.0
            else:  # Semaine
                entry.mood = 3
                entry.stress_level = 3
                entry.sleep_hours = 7.0
            
            entry.date = date.strftime("%Y-%m-%d")
            weekly_entries.append(entry)
        
        def mock_get_weekend_pattern(user_id, start_date, end_date):
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            return [
                entry for entry in weekly_entries 
                if start <= datetime.strptime(entry.date, "%Y-%m-%d").date() <= end
            ]
        
        service.mood_repository.get_user_mood_entries_by_date_range.side_effect = mock_get_weekend_pattern
        
        trends = service.get_weekly_mood_trends("user-123", weeks=1)
        week_trend = trends[0]
        
        # Moyenne devrait refléter le mix semaine/week-end
        # 5 jours à 3 + 2 jours à 4 = (5*3 + 2*4) / 7 = 23/7 ≈ 3.29
        expected_avg = (5 * 3 + 2 * 4) / 7
        print(f"Expected average mood: {week_trend}")
        assert abs(week_trend.average_mood - expected_avg) < 0.01

    def test_aggregation_with_missing_days(self, stats_service_with_real_data):
        """Test d'agrégation avec des jours manquants"""
        service = stats_service_with_real_data
        
        # Simuler des données avec des trous (jours manqués)
        def mock_get_sparse_entries(user_id, start_date, end_date):
            # Simuler que l'utilisateur a manqué plusieurs jours
            return [
                Mock(mood=4, stress_level=2, sleep_hours=8.0),  # Lundi
                Mock(mood=3, stress_level=3, sleep_hours=7.0),  # Mercredi (mardi manqué)
                Mock(mood=5, stress_level=1, sleep_hours=8.5),  # Vendredi (jeudi manqué)
                # Week-end manqué
            ]
        
        service.mood_repository.get_user_mood_entries_by_date_range.side_effect = mock_get_sparse_entries
        
        trends = service.get_weekly_mood_trends("user-123", weeks=1)
        week_trend = trends[0]
        
        # Seulement 3 entrées sur 7 jours possibles
        assert week_trend.entries_count == 3
        
        # Moyenne calculée uniquement sur les jours avec données
        assert week_trend.average_mood == (4 + 3 + 5) / 3

    def test_multiple_weeks_aggregation_comparison(self, stats_service_with_real_data):
        """Test de comparaison d'agrégation sur plusieurs semaines"""
        service = stats_service_with_real_data
        
        def mock_get_multiple_weeks(user_id, start_date, end_date):
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            
            # Déterminer quelle semaine et retourner des données différentes
            today = datetime.now().date()
            
            if start >= today - timedelta(days=6):
                # Semaine actuelle - bonne
                return [Mock(mood=4, stress_level=2, sleep_hours=8.0) for _ in range(5)]
            elif start >= today - timedelta(days=13):
                # Semaine précédente - moyenne
                return [Mock(mood=3, stress_level=3, sleep_hours=7.0) for _ in range(4)]
            elif start >= today - timedelta(days=20):
                # Il y a 2 semaines - moins bonne
                return [Mock(mood=2, stress_level=4, sleep_hours=6.5) for _ in range(3)]
            else:
                # Plus ancien - données limitées
                return [Mock(mood=2, stress_level=4, sleep_hours=6.0)]
        
        service.mood_repository.get_user_mood_entries_by_date_range.side_effect = mock_get_multiple_weeks
        
        trends = service.get_weekly_mood_trends("user-123", weeks=4)
        
        assert len(trends) == 4
        
        # Vérifier l'ordre chronologique (plus ancien en premier)
        assert trends[0].average_mood <= trends[1].average_mood <= trends[2].average_mood <= trends[3].average_mood
        
        # Vérifier la progression des données
        assert trends[-1].entries_count >= trends[0].entries_count  # Plus de données récentes
