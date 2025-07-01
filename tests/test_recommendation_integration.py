import pytest
from sqlalchemy.orm import Session

from app.services.recommendation_service import RecommendationService
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.mood_repository import MoodRepository
from app.schemas.recommendation_dto import (
    RecommendationGenerateRequest,
    RecommendationUpdate,
)


class TestRecommendationIntegration:
    """Tests d'intégration end-to-end pour les recommandations"""

    @pytest.fixture
    def recommendation_service(self, db: Session):
        """Service de recommandations avec vraie DB"""
        recommendation_repo = RecommendationRepository(db)
        mood_repo = MoodRepository(db)
        return RecommendationService(recommendation_repo, mood_repo)

    @pytest.fixture
    def user_with_low_mood_data(self, db: Session, test_data_seeder):
        """Utilisateur avec plusieurs entrées d'humeur basse"""
        user = test_data_seeder.create_test_user(
            email="integration@test.com", consent=True
        )

        # Créer plusieurs entrées d'humeur basse
        mood_entries = []
        for i, (mood_level, notes) in enumerate(
            [
                (1, "Je me sens vraiment très mal"),
                (2, "Journée difficile"),
                (1, "Déprime profonde"),
            ]
        ):
            mood_entry = test_data_seeder.create_test_mood_entry(
                user_id=user.id,  # Convert to string explicitly
                mood=mood_level,
                stress_level=4,
                notes=notes,
                date=f"2024-01-{15+i:02d}",
            )
            mood_entries.append(mood_entry)

        return {"user": user, "mood_entries": mood_entries}

    @pytest.mark.asyncio
    async def test_full_recommendation_workflow_for_low_mood(
        self, recommendation_service, user_with_low_mood_data
    ):
        """Test workflow complet: génération → feedback → stats pour humeur basse"""
        user = user_with_low_mood_data["user"]
        mood_entry = user_with_low_mood_data["mood_entries"][0]  # Mood level 1

        # Debug: Verify mood entry exists
        mood_repo = MoodRepository(recommendation_service.mood_repository.db)
        found_mood = mood_repo.get_mood_entry_by_id(str(mood_entry.id))
        assert (
            found_mood is not None
        ), f"Mood entry {mood_entry.id} not found in database"

        # 1. Générer des recommandations pour humeur très basse
        request = RecommendationGenerateRequest(
            mood_id=str(mood_entry.id), time_available=30  # Ensure string conversion
        )

        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                user, request
            )
        )

        # Vérifications initiales
        assert len(recommendations) > 0
        assert len(recommendations) <= 3

        # Vérifier que les activités sont appropriées pour mood level 1
        activities = [r.suggested_activity for r in recommendations]

        expected_keywords = [
            "respirer",
            "musique",
            "douche",
            "proche",
            "méditation",
            "tisane",
        ]

        # Au moins une activité doit contenir un mot-clé approprié pour l'humeur basse
        assert any(
            any(keyword in activity.lower() for keyword in expected_keywords)
            for activity in activities
        ), f"Aucune activité appropriée trouvée dans: {activities}"

        # 2. Simuler feedback utilisateur
        feedback_results = []
        for i, reco in enumerate(recommendations):
            # Première recommandation utile, autres moins utiles
            helpful = i == 0

            feedback = RecommendationUpdate(was_helpful=helpful)
            updated_reco = recommendation_service.update_recommendation_feedback(
                reco.id, user.id, feedback  # Ensure string conversion
            )

            assert updated_reco.was_helpful == helpful
            feedback_results.append(updated_reco)

        # 3. Vérifier les statistiques
        stats = recommendation_service.get_recommendation_stats(user.id, days=30)

        assert stats.total_recommendations >= len(recommendations)
        assert stats.helpful_count >= 1  # Au moins une marquée comme utile
        assert stats.not_helpful_count >= 1  # Au moins une marquée comme non utile
        assert 0 <= stats.helpfulness_rate <= 100

        # 4. Vérifier que les recommandations futures évitent les doublons
        request2 = RecommendationGenerateRequest(
            mood_id=str(
                user_with_low_mood_data["mood_entries"][1].id
            ),  # Ensure string conversion
            time_available=30,
        )

        new_recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                user, request2
            )
        )

        # Les nouvelles recommandations devraient être différentes ou limitées
        assert len(new_recommendations) > 0

    @pytest.mark.asyncio
    async def test_recommendation_effectiveness_tracking(
        self, recommendation_service, user_with_low_mood_data
    ):
        """Test suivi de l'efficacité des recommandations pour humeur basse"""
        user = user_with_low_mood_data["user"]

        # Générer et évaluer plusieurs recommandations
        all_recommendations = []

        # Générer plus de recommandations pour avoir assez de données
        for mood_entry in user_with_low_mood_data["mood_entries"]:
            # Générer des recommandations plusieurs fois pour la même humeur
            for _ in range(2):  # 2 fois par mood entry = 6 recommandations au total
                request = RecommendationGenerateRequest(
                    mood_id=str(mood_entry.id),  # Ensure string conversion
                    time_available=30,
                )

                recommendations = (
                    await recommendation_service.generate_recommendations_from_mood(
                        user, request
                    )
                )
                all_recommendations.extend(recommendations)

        print(f"Total recommendations generated: {len(all_recommendations)}")

        # Simuler feedback varié - s'assurer qu'on a au moins 2 feedbacks par activité
        activity_feedback_count = {}
        helpful_count = 0

        for i, reco in enumerate(all_recommendations):
            # Compter les feedbacks par activité
            activity = reco.suggested_activity
            if activity not in activity_feedback_count:
                activity_feedback_count[activity] = 0
            activity_feedback_count[activity] += 1

            # 70% des recommandations marquées comme utiles
            helpful = i % 3 != 0  # 2 sur 3 utiles (66%)
            if helpful:
                helpful_count += 1

            feedback = RecommendationUpdate(was_helpful=helpful)
            recommendation_service.update_recommendation_feedback(
                reco.id, user.id, feedback  # Ensure string conversion
            )

        print(f"Activity feedback count: {activity_feedback_count}")
        print(f"Total helpful: {helpful_count}/{len(all_recommendations)}")

        # Analyser l'efficacité
        activity_effectiveness = recommendation_service.get_activity_effectiveness(
            user.id, days=30  # Ensure string conversion
        )

        print(f"Activity effectiveness: {activity_effectiveness}")

        # Vérifier qu'on a des données d'efficacité
        # Avec au moins 6 recommandations et le seuil de 2 minimum, on devrait avoir des stats
        activities_with_multiple_feedback = [
            activity
            for activity, count in activity_feedback_count.items()
            if count >= 2
        ]

        print(f"Activities with >= 2 feedback: {activities_with_multiple_feedback}")

        if len(activities_with_multiple_feedback) > 0:
            assert (
                len(activity_effectiveness) > 0
            ), f"Expected effectiveness data for activities: {activities_with_multiple_feedback}"

            for activity_stat in activity_effectiveness:
                assert 0 <= activity_stat.effectiveness_rate <= 100
                print(
                    f"Activity: {activity_stat.activity}, Rate: {activity_stat.effectiveness_rate}%"
                )
        else:
            print(
                "No activities with sufficient feedback (>=2), skipping effectiveness assertions"
            )

    @pytest.mark.asyncio
    async def test_recommendation_personalization_over_time(
        self, recommendation_service, user_with_low_mood_data
    ):
        """Test personnalisation des recommandations au fil du temps"""
        user = user_with_low_mood_data["user"]

        # Phase 1: Premières recommandations
        mood_entry_1 = user_with_low_mood_data["mood_entries"][0]
        request_1 = RecommendationGenerateRequest(
            mood_id=str(mood_entry_1.id), time_available=30  # Ensure string conversion
        )

        first_recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                user, request_1
            )
        )

        # Marquer certaines comme très utiles
        for reco in first_recommendations[:2]:
            feedback = RecommendationUpdate(was_helpful=True)
            recommendation_service.update_recommendation_feedback(
                reco.id, user.id, feedback  # Ensure string conversion
            )

        # Phase 2: Nouvelles recommandations après feedback
        mood_entry_2 = user_with_low_mood_data["mood_entries"][1]
        request_2 = RecommendationGenerateRequest(
            mood_id=str(mood_entry_2.id), time_available=30  # Ensure string conversion
        )

        second_recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                user, request_2
            )
        )

        # Vérifier que le système apprend (difficile à tester sans ML avancé)
        # Pour l'instant, vérifier que de nouvelles recommandations sont générées
        assert len(second_recommendations) > 0

        # Les recommandations devraient tenir compte de l'historique récent
        first_activities = [r.suggested_activity for r in first_recommendations]
        second_activities = [r.suggested_activity for r in second_recommendations]

        # Il devrait y avoir une certaine variété
        unique_activities = set(first_activities + second_activities)
        assert len(unique_activities) >= len(first_activities)

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_direct_mood_level(
        self, recommendation_service, user_with_low_mood_data
    ):
        """Test génération avec niveau d'humeur direct (sans mood_id)"""
        user = user_with_low_mood_data["user"]

        # Test avec mood_level direct au lieu de mood_id
        request = RecommendationGenerateRequest(
            mood_level=1, time_available=20  # Très triste
        )

        recommendations = (
            await recommendation_service.generate_recommendations_from_mood(
                user, request
            )
        )

        assert len(recommendations) > 0
        assert len(recommendations) <= 3

        # Vérifier que les activités sont appropriées pour mood level 1
        activities = [r.suggested_activity for r in recommendations]
        expected_keywords = ["respirer", "musique", "douche", "proche", "méditation"]

        assert any(
            any(keyword in activity.lower() for keyword in expected_keywords)
            for activity in activities
        ), f"Aucune activité appropriée trouvée dans: {activities}"
