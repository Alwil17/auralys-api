import pytest
from unittest.mock import Mock
from datetime import datetime

from app.services.recommendation_service import RecommendationService
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.mood_repository import MoodRepository
from app.schemas.recommendation_dto import (
    RecommendationGenerateRequest,
    ActivitySuggestion,
)
from app.db.models.user import User
from app.db.models.mood_entry import MoodEntry
from app.db.models.recommendation import Recommendation
from fastapi import HTTPException


class TestRecommendationService:
    """Tests pour le service de recommandations"""

    @pytest.fixture
    def mock_recommendation_repository(self):
        """Mock du repository de recommandations"""
        return Mock(spec=RecommendationRepository)

    @pytest.fixture
    def mock_mood_repository(self):
        """Mock du repository d'humeur"""
        return Mock(spec=MoodRepository)

    @pytest.fixture
    def recommendation_service(
        self, mock_recommendation_repository, mock_mood_repository
    ):
        """Service de recommandations avec mocks"""
        return RecommendationService(
            mock_recommendation_repository, mock_mood_repository
        )

    @pytest.fixture
    def test_user_with_consent(self):
        """Utilisateur de test avec consentement"""
        user = Mock(spec=User)
        user.id = "user-123"
        user.consent = True
        return user

    @pytest.fixture
    def test_user_no_consent(self):
        """Utilisateur de test sans consentement"""
        user = Mock(spec=User)
        user.id = "user-456"
        user.consent = False
        return user

    @pytest.fixture
    def low_mood_entry(self):
        """Entrée d'humeur basse pour les tests"""
        mood_entry = Mock(spec=MoodEntry)
        mood_entry.id = "mood-123"
        mood_entry.user_id = "user-123"
        mood_entry.mood = 1  # Très triste
        mood_entry.stress_level = 4
        mood_entry.notes = "Je me sens très mal aujourd'hui"
        return mood_entry

    @pytest.fixture
    def high_mood_entry(self):
        """Entrée d'humeur élevée pour les tests"""
        mood_entry = Mock(spec=MoodEntry)
        mood_entry.id = "mood-456"
        mood_entry.user_id = "user-123"
        mood_entry.mood = 5  # Très heureux
        mood_entry.stress_level = 1
        mood_entry.notes = "Je me sens fantastique"
        return mood_entry

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_low_mood_level_1(
        self,
        recommendation_service,
        test_user_with_consent,
        low_mood_entry,
        mock_mood_repository,
        mock_recommendation_repository,
    ):
        """Test génération de recommandations pour humeur très basse (niveau 1)"""
        # Configuration des mocks
        mock_mood_repository.get_mood_entry_by_id.return_value = low_mood_entry
        mock_recommendation_repository.get_recent_recommendations.return_value = []

        # Mock de création de recommandation avec tous les champs requis
        def create_recommendation_side_effect(user_id, reco_data):
            recommendation = Mock(spec=Recommendation)
            recommendation.id = f"reco-{len(mock_recommendation_repository.create_recommendation.call_args_list)}"
            recommendation.user_id = user_id
            recommendation.suggested_activity = reco_data.suggested_activity
            recommendation.mood_id = reco_data.mood_id
            recommendation.recommendation_type = (
                reco_data.recommendation_type or "mood_based"
            )
            recommendation.confidence_score = reco_data.confidence_score or 0.8
            recommendation.timestamp = datetime.now()
            recommendation.was_helpful = None
            return recommendation

        mock_recommendation_repository.create_recommendation.side_effect = (
            create_recommendation_side_effect
        )

        # Requête pour mood très bas
        request = RecommendationGenerateRequest(mood_id="mood-123", time_available=30)

        # Exécuter
        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                test_user_with_consent, request
            )
        )

        # Vérifications
        assert len(recommendations) > 0
        assert len(recommendations) <= 3  # Maximum 3 recommandations

        # Vérifier que les activités sont appropriées pour l'humeur basse
        activities = [r.suggested_activity for r in recommendations]

        # Activités attendues pour mood = 1 (calming, low difficulty)
        expected_keywords = ["respirer", "musique", "douche", "proche", "méditation"]

        # Au moins une activité doit contenir un mot-clé approprié
        assert any(
            any(keyword in activity.lower() for keyword in expected_keywords)
            for activity in activities
        )

        # Vérifier les appels
        mock_mood_repository.get_mood_entry_by_id.assert_called_once_with("mood-123")
        assert mock_recommendation_repository.create_recommendation.call_count == len(
            recommendations
        )

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_low_mood_level_2(
        self,
        recommendation_service,
        test_user_with_consent,
        mock_mood_repository,
        mock_recommendation_repository,
    ):
        """Test génération de recommandations pour humeur basse (niveau 2)"""
        # Entrée d'humeur niveau 2
        mood_entry = Mock(spec=MoodEntry)
        mood_entry.id = "mood-789"
        mood_entry.user_id = "user-123"
        mood_entry.mood = 2  # Triste

        mock_mood_repository.get_mood_entry_by_id.return_value = mood_entry
        mock_recommendation_repository.get_recent_recommendations.return_value = []

        # Mock création avec tous les champs requis
        recommendations_created = []

        def create_recommendation_side_effect(user_id, reco_data):
            recommendation = Mock(spec=Recommendation)
            recommendation.id = f"reco-{len(recommendations_created)}"
            recommendation.user_id = user_id
            recommendation.suggested_activity = reco_data.suggested_activity
            recommendation.mood_id = reco_data.mood_id
            recommendation.recommendation_type = (
                reco_data.recommendation_type or "mood_based"
            )
            recommendation.confidence_score = reco_data.confidence_score or 0.7
            recommendation.timestamp = datetime.now()
            recommendation.was_helpful = None
            recommendations_created.append(recommendation)
            return recommendation

        mock_recommendation_repository.create_recommendation.side_effect = (
            create_recommendation_side_effect
        )

        request = RecommendationGenerateRequest(mood_id="mood-789", time_available=45)

        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                test_user_with_consent, request
            )
        )

        # Vérifications spécifiques au niveau 2
        activities = [r.suggested_activity for r in recommendations]

        # Mots-clés attendus pour mood = 2
        expected_keywords = ["promenade", "journal", "tisane", "yoga", "cuisiner"]

        assert any(
            any(keyword in activity.lower() for keyword in expected_keywords)
            for activity in activities
        )

        # Vérifier que les scores de confiance sont appropriés
        for reco in recommendations:
            assert hasattr(reco, "confidence_score")
            assert reco.confidence_score > 0

    def test_get_activities_for_low_mood(self, recommendation_service):
        """Test récupération d'activités pour humeur basse"""
        # Test pour mood level 1
        activities_level_1 = recommendation_service._get_activities_for_mood(1, 30)

        assert len(activities_level_1) > 0

        # Vérifier que les activités sont appropriées (calming, easy)
        calming_activities = [
            a for a in activities_level_1 if a.mood_impact == "calming"
        ]
        easy_activities = [a for a in activities_level_1 if a.difficulty == "easy"]

        assert len(calming_activities) > 0
        assert len(easy_activities) > 0

        # Test pour mood level 2
        activities_level_2 = recommendation_service._get_activities_for_mood(2, 30)

        assert len(activities_level_2) > 0

        # Vérifier les temps d'activité appropriés
        short_activities = [a for a in activities_level_2 if a.estimated_time <= 30]
        assert len(short_activities) > 0

    def test_calculate_confidence_score_for_low_mood(self, recommendation_service):
        """Test calcul du score de confiance pour humeur basse"""
        # Activité calmante pour humeur basse
        calming_activity = ActivitySuggestion(
            activity="Méditation guidée",
            description="Calmer l'esprit",
            estimated_time=15,
            mood_impact="calming",
            difficulty="easy",
            category="mental",
        )

        # Score pour mood level 1
        score_1 = recommendation_service._calculate_confidence_score(
            1, calming_activity
        )
        assert score_1 > 0.7  # Devrait être élevé pour activité appropriée

        # Score pour mood level 2
        score_2 = recommendation_service._calculate_confidence_score(
            2, calming_activity
        )
        assert score_2 > 0.7

        # Activité énergisante pour humeur basse (moins appropriée)
        energizing_activity = ActivitySuggestion(
            activity="Course intensive",
            description="Sport intense",
            estimated_time=60,
            mood_impact="energizing",
            difficulty="hard",
            category="physical",
        )

        score_energizing = recommendation_service._calculate_confidence_score(
            1, energizing_activity
        )
        assert score_energizing < score_1  # Devrait être plus bas

    def test_select_diverse_activities_for_low_mood(self, recommendation_service):
        """Test sélection d'activités diversifiées pour humeur basse"""
        activities = [
            ActivitySuggestion(
                activity="Respiration",
                description="",
                estimated_time=5,
                mood_impact="calming",
                difficulty="easy",
                category="mental",
            ),
            ActivitySuggestion(
                activity="Douche chaude",
                description="",
                estimated_time=15,
                mood_impact="calming",
                difficulty="easy",
                category="physical",
            ),
            ActivitySuggestion(
                activity="Appel proche",
                description="",
                estimated_time=20,
                mood_impact="positive",
                difficulty="medium",
                category="social",
            ),
            ActivitySuggestion(
                activity="Musique douce",
                description="",
                estimated_time=10,
                mood_impact="calming",
                difficulty="easy",
                category="mental",
            ),
        ]

        selected = recommendation_service._select_diverse_activities(activities, 3)

        assert len(selected) == 3

        # Vérifier la diversité des catégories
        categories = [a.category for a in selected]
        assert len(set(categories)) >= 2  # Au moins 2 catégories différentes

    @pytest.mark.asyncio
    async def test_generate_recommendations_no_consent(
        self, recommendation_service, test_user_no_consent
    ):
        """Test rejet si pas de consentement RGPD"""
        request = RecommendationGenerateRequest(mood_level=1)

        with pytest.raises(HTTPException) as exc_info:
            await recommendation_service.generate_recommendations_from_mood(
                test_user_no_consent, request
            )

        assert exc_info.value.status_code == 403
        assert "Consentement requis" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_generate_recommendations_mood_not_found(
        self, recommendation_service, test_user_with_consent, mock_mood_repository
    ):
        """Test erreur si entrée d'humeur non trouvée"""
        mock_mood_repository.get_mood_entry_by_id.return_value = None

        request = RecommendationGenerateRequest(mood_id="non-existent")

        with pytest.raises(HTTPException) as exc_info:
            await recommendation_service.generate_recommendations_from_mood(
                test_user_with_consent, request
            )

        assert exc_info.value.status_code == 404
        assert "Entrée d'humeur non trouvée" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_recent_duplicates(
        self,
        recommendation_service,
        test_user_with_consent,
        low_mood_entry,
        mock_mood_repository,
        mock_recommendation_repository,
    ):
        """Test évitement des doublons avec recommandations récentes"""
        mock_mood_repository.get_mood_entry_by_id.return_value = low_mood_entry

        # Recommandations récentes qui créent des doublons
        recent_reco = Mock(spec=Recommendation)
        recent_reco.suggested_activity = "Respirer profondément pendant 5 minutes"
        mock_recommendation_repository.get_recent_recommendations.return_value = [
            recent_reco
        ]

        # Mock création avec tous les champs
        def create_recommendation_side_effect(user_id, reco_data):
            recommendation = Mock(spec=Recommendation)
            recommendation.id = "new-reco-1"
            recommendation.user_id = user_id
            recommendation.suggested_activity = reco_data.suggested_activity
            recommendation.mood_id = reco_data.mood_id
            recommendation.recommendation_type = (
                reco_data.recommendation_type or "mood_based"
            )
            recommendation.confidence_score = reco_data.confidence_score or 0.8
            recommendation.timestamp = datetime.now()
            recommendation.was_helpful = None
            return recommendation

        mock_recommendation_repository.create_recommendation.side_effect = (
            create_recommendation_side_effect
        )

        request = RecommendationGenerateRequest(mood_id="mood-123")

        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                test_user_with_consent, request
            )
        )

        # Vérifier que les nouvelles recommandations évitent les doublons
        activities = [r.suggested_activity for r in recommendations]
        assert "Respirer profondément pendant 5 minutes" not in activities

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_time_constraints(
        self,
        recommendation_service,
        test_user_with_consent,
        low_mood_entry,
        mock_mood_repository,
        mock_recommendation_repository,
    ):
        """Test génération avec contraintes de temps"""
        mock_mood_repository.get_mood_entry_by_id.return_value = low_mood_entry
        mock_recommendation_repository.get_recent_recommendations.return_value = []

        # Mock création avec tous les champs
        def create_recommendation_side_effect(user_id, reco_data):
            recommendation = Mock(spec=Recommendation)
            recommendation.id = "time-constrained-reco"
            recommendation.user_id = user_id
            recommendation.suggested_activity = reco_data.suggested_activity
            recommendation.mood_id = reco_data.mood_id
            recommendation.recommendation_type = (
                reco_data.recommendation_type or "mood_based"
            )
            recommendation.confidence_score = reco_data.confidence_score or 0.8
            recommendation.timestamp = datetime.now()
            recommendation.was_helpful = None
            return recommendation

        mock_recommendation_repository.create_recommendation.side_effect = (
            create_recommendation_side_effect
        )

        # Test avec peu de temps disponible
        request = RecommendationGenerateRequest(
            mood_id="mood-123", time_available=10  # Seulement 10 minutes
        )

        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                test_user_with_consent, request
            )
        )

        # Vérifier que des recommandations ont été générées même avec peu de temps
        assert len(recommendations) > 0

    @pytest.mark.parametrize(
        "mood_level,expected_mood_impact",
        [
            (1, "calming"),
            (2, "calming"),
            (3, "positive"),
            (4, "positive"),
            (5, "energizing"),
        ],
    )
    def test_mood_level_to_activity_mapping(
        self, recommendation_service, mood_level, expected_mood_impact
    ):
        """Test mapping entre niveau d'humeur et type d'activité"""
        activities = recommendation_service._get_activities_for_mood(mood_level, 30)

        # Pour les humeurs basses, vérifier qu'on a des activités calmantes
        if mood_level <= 2:
            calming_activities = [a for a in activities if a.mood_impact == "calming"]
            assert len(calming_activities) > 0

        # Pour les bonnes humeurs, vérifier qu'on a des activités positives/énergisantes
        elif mood_level >= 4:
            positive_activities = [
                a for a in activities if a.mood_impact in ["positive", "energizing"]
            ]
            assert len(positive_activities) > 0
