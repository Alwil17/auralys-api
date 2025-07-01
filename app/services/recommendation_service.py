from typing import List, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import random

from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.mood_repository import MoodRepository
from app.schemas.recommendation_dto import (
    RecommendationCreate,
    RecommendationUpdate,
    RecommendationOut,
    RecommendationGenerateRequest,
    RecommendationStats,
    ActivitySuggestion
)
from app.db.models.user import User


class RecommendationService:
    def __init__(self, recommendation_repository: RecommendationRepository, mood_repository: MoodRepository = None):
        self.recommendation_repository = recommendation_repository
        self.mood_repository = mood_repository
        self.activity_database = self._initialize_activity_database()

    def _initialize_activity_database(self) -> dict:
        """Base de données d'activités organisées par niveau d'humeur et contexte"""
        return {
            1: {  # Très triste/déprimé
                "immediate": [
                    ActivitySuggestion(
                        activity="Respirer profondément pendant 5 minutes",
                        description="Exercice de respiration pour calmer l'anxiété",
                        estimated_time=5,
                        mood_impact="calming",
                        difficulty="easy",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Écouter une musique douce",
                        description="Musique apaisante pour réconforter",
                        estimated_time=15,
                        mood_impact="calming",
                        difficulty="easy",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Prendre une douche chaude",
                        description="L'eau chaude peut aider à se détendre",
                        estimated_time=15,
                        mood_impact="calming",
                        difficulty="easy",
                        category="physical"
                    )
                ],
                "longer": [
                    ActivitySuggestion(
                        activity="Appeler un proche de confiance",
                        description="Parler avec quelqu'un peut aider",
                        estimated_time=30,
                        mood_impact="positive",
                        difficulty="medium",
                        category="social"
                    ),
                    ActivitySuggestion(
                        activity="Regarder un film réconfortant",
                        description="Distraction positive avec un contenu familier",
                        estimated_time=90,
                        mood_impact="positive",
                        difficulty="easy",
                        category="mental"
                    )
                ]
            },
            2: {  # Triste
                "immediate": [
                    ActivitySuggestion(
                        activity="Faire une courte promenade",
                        description="Marcher aide à changer d'environnement",
                        estimated_time=15,
                        mood_impact="positive",
                        difficulty="easy",
                        category="physical"
                    ),
                    ActivitySuggestion(
                        activity="Tenir un journal de gratitude",
                        description="Noter 3 choses positives de la journée",
                        estimated_time=10,
                        mood_impact="positive",
                        difficulty="easy",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Boire une tisane chaude",
                        description="Moment de réconfort et de chaleur",
                        estimated_time=10,
                        mood_impact="calming",
                        difficulty="easy",
                        category="physical"
                    )
                ],
                "longer": [
                    ActivitySuggestion(
                        activity="Pratiquer du yoga doux",
                        description="Étirements et détente pour le corps et l'esprit",
                        estimated_time=30,
                        mood_impact="calming",
                        difficulty="medium",
                        category="physical"
                    ),
                    ActivitySuggestion(
                        activity="Cuisiner un plat réconfortant",
                        description="Activité créative et nourrissante",
                        estimated_time=45,
                        mood_impact="positive",
                        difficulty="medium",
                        category="creative"
                    )
                ]
            },
            3: {  # Neutre
                "immediate": [
                    ActivitySuggestion(
                        activity="Faire 10 minutes de méditation",
                        description="Moment de centrage et de clarté",
                        estimated_time=10,
                        mood_impact="calming",
                        difficulty="medium",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Organiser son espace de travail",
                        description="Activité productive qui donne du contrôle",
                        estimated_time=20,
                        mood_impact="positive",
                        difficulty="easy",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Lire quelques pages d'un livre",
                        description="Stimulation mentale douce",
                        estimated_time=20,
                        mood_impact="positive",
                        difficulty="easy",
                        category="mental"
                    )
                ],
                "longer": [
                    ActivitySuggestion(
                        activity="Apprendre quelque chose de nouveau en ligne",
                        description="Cours ou tutoriel sur un sujet d'intérêt",
                        estimated_time=60,
                        mood_impact="positive",
                        difficulty="medium",
                        category="mental"
                    ),
                    ActivitySuggestion(
                        activity="Planifier une activité future",
                        description="Donner quelque chose à anticiper positivement",
                        estimated_time=30,
                        mood_impact="positive",
                        difficulty="medium",
                        category="mental"
                    )
                ]
            },
            4: {  # Bonne humeur
                "immediate": [
                    ActivitySuggestion(
                        activity="Partager sa joie avec un ami",
                        description="Message ou appel pour partager les bonnes nouvelles",
                        estimated_time=15,
                        mood_impact="positive",
                        difficulty="easy",
                        category="social"
                    ),
                    ActivitySuggestion(
                        activity="Danser sur sa musique préférée",
                        description="Exprimer sa joie par le mouvement",
                        estimated_time=10,
                        mood_impact="energizing",
                        difficulty="easy",
                        category="physical"
                    ),
                    ActivitySuggestion(
                        activity="Faire un compliment à quelqu'un",
                        description="Répandre la positivité autour de soi",
                        estimated_time=5,
                        mood_impact="positive",
                        difficulty="easy",
                        category="social"
                    )
                ],
                "longer": [
                    ActivitySuggestion(
                        activity="Commencer un projet créatif",
                        description="Canaliser l'énergie positive dans la création",
                        estimated_time=60,
                        mood_impact="positive",
                        difficulty="medium",
                        category="creative"
                    ),
                    ActivitySuggestion(
                        activity="Planifier une sortie avec des amis",
                        description="Organiser un moment social agréable",
                        estimated_time=30,
                        mood_impact="positive",
                        difficulty="medium",
                        category="social"
                    )
                ]
            },
            5: {  # Très bonne humeur
                "immediate": [
                    ActivitySuggestion(
                        activity="Faire de l'exercice énergique",
                        description="Canaliser l'énergie positive dans le sport",
                        estimated_time=30,
                        mood_impact="energizing",
                        difficulty="medium",
                        category="physical"
                    ),
                    ActivitySuggestion(
                        activity="Aider quelqu'un dans le besoin",
                        description="Utiliser sa positivité pour aider les autres",
                        estimated_time=30,
                        mood_impact="positive",
                        difficulty="medium",
                        category="social"
                    ),
                    ActivitySuggestion(
                        activity="Prendre des photos de moments heureux",
                        description="Capturer et préserver ces bons moments",
                        estimated_time=15,
                        mood_impact="positive",
                        difficulty="easy",
                        category="creative"
                    )
                ],
                "longer": [
                    ActivitySuggestion(
                        activity="Organiser une activité surprise pour un proche",
                        description="Partager sa joie en créant du bonheur pour les autres",
                        estimated_time=120,
                        mood_impact="positive",
                        difficulty="hard",
                        category="social"
                    ),
                    ActivitySuggestion(
                        activity="Démarrer un nouveau hobby",
                        description="Utiliser l'énergie positive pour explorer de nouveaux intérêts",
                        estimated_time=90,
                        mood_impact="positive",
                        difficulty="medium",
                        category="creative"
                    )
                ]
            }
        }

    async def generate_recommendations_from_mood(
        self, 
        user: User, 
        request: RecommendationGenerateRequest
    ) -> List[RecommendationOut]:
        """Générer des recommandations basées sur une entrée d'humeur"""
        
        # Vérifier le consentement RGPD
        if not user.consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentement requis pour générer des recommandations"
            )

        mood_level = None
        mood_entry = None
        
        # Récupérer le niveau d'humeur
        if request.mood_id and self.mood_repository:
            mood_entry = self.mood_repository.get_mood_entry_by_id(request.mood_id)
            if not mood_entry or mood_entry.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Entrée d'humeur non trouvée"
                )
            mood_level = mood_entry.mood
        elif request.mood_level:
            mood_level = request.mood_level
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Soit mood_id soit mood_level doit être fourni"
            )

        # Vérifier les recommandations récentes pour éviter les doublons
        recent_recommendations = self.recommendation_repository.get_recent_recommendations(
            user.id, hours=6
        )
        recent_activities = [r.suggested_activity for r in recent_recommendations]

        # Générer les recommandations
        recommendations = []
        activities = self._get_activities_for_mood(mood_level, request.time_available or 30)
        
        # Filtrer les activités déjà recommandées récemment
        available_activities = [a for a in activities if a.activity not in recent_activities]
        
        # Si toutes les activités ont été recommandées récemment, prendre les meilleures quand même
        if not available_activities:
            available_activities = activities[:2]
        
        # Sélectionner 2-3 recommandations variées
        selected_activities = self._select_diverse_activities(
            available_activities, 
            count=min(3, len(available_activities))
        )

        for activity in selected_activities:
            recommendation_data = RecommendationCreate(
                suggested_activity=activity.activity,
                mood_id=request.mood_id,
                recommendation_type="mood_based",
                confidence_score=self._calculate_confidence_score(mood_level, activity)
            )
            
            recommendation = self.recommendation_repository.create_recommendation(
                user.id, recommendation_data
            )
            recommendations.append(RecommendationOut.model_validate(recommendation))

        return recommendations

    def _get_activities_for_mood(self, mood_level: int, time_available: int) -> List[ActivitySuggestion]:
        """Récupérer les activités appropriées pour un niveau d'humeur donné"""
        mood_activities = self.activity_database.get(mood_level, self.activity_database[3])
        
        # Choisir entre activités immédiates ou plus longues selon le temps disponible
        if time_available <= 20:
            activities = mood_activities.get("immediate", [])
        else:
            activities = mood_activities.get("immediate", []) + mood_activities.get("longer", [])
        
        # Filtrer par temps disponible
        suitable_activities = [
            a for a in activities 
            if a.estimated_time <= time_available
        ]
        
        return suitable_activities if suitable_activities else activities[:2]

    def _select_diverse_activities(self, activities: List[ActivitySuggestion], count: int) -> List[ActivitySuggestion]:
        """Sélectionner des activités diversifiées (différentes catégories)"""
        if len(activities) <= count:
            return activities
        
        selected = []
        categories_used = set()
        
        # D'abord, prendre une activité de chaque catégorie
        for activity in activities:
            if activity.category not in categories_used and len(selected) < count:
                selected.append(activity)
                categories_used.add(activity.category)
        
        # Compléter avec les meilleures activités restantes
        remaining_activities = [a for a in activities if a not in selected]
        while len(selected) < count and remaining_activities:
            selected.append(remaining_activities.pop(0))
        
        return selected

    def _calculate_confidence_score(self, mood_level: int, activity: ActivitySuggestion) -> float:
        """Calculer un score de confiance pour la recommandation"""
        base_score = 0.7
        
        # Ajuster selon le niveau d'humeur
        if mood_level in [1, 2]:  # Humeurs basses
            if activity.mood_impact == "calming":
                base_score += 0.2
        elif mood_level in [4, 5]:  # Bonnes humeurs
            if activity.mood_impact in ["positive", "energizing"]:
                base_score += 0.2
        
        # Ajuster selon la difficulté
        if activity.difficulty == "easy":
            base_score += 0.1
        
        return min(1.0, base_score)

    def update_recommendation_feedback(
        self, 
        recommendation_id: str, 
        user_id: str, 
        feedback: RecommendationUpdate
    ) -> RecommendationOut:
        """Mettre à jour le feedback d'une recommandation"""
        recommendation = self.recommendation_repository.get_recommendation_by_id(recommendation_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommandation non trouvée"
            )
        
        if recommendation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette recommandation"
            )
        
        updated_recommendation = self.recommendation_repository.update_recommendation_feedback(
            recommendation_id, feedback
        )
        
        return RecommendationOut.model_validate(updated_recommendation)

    def get_user_recommendations(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[RecommendationOut]:
        """Récupérer les recommandations d'un utilisateur"""
        recommendations = self.recommendation_repository.get_user_recommendations(
            user_id, skip, limit
        )
        return [RecommendationOut.model_validate(r) for r in recommendations]

    def get_recommendation_stats(self, user_id: str, days: int = 30) -> RecommendationStats:
        """Obtenir les statistiques de recommandations"""
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de jours doit être entre 1 et 365"
            )

        stats = self.recommendation_repository.get_recommendation_stats(user_id, days)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        return RecommendationStats(
            total_recommendations=stats["total_recommendations"],
            helpful_count=stats["helpful_count"],
            not_helpful_count=stats["not_helpful_count"],
            pending_feedback=stats["pending_feedback"],
            helpfulness_rate=stats["helpfulness_rate"],
            most_recommended_activity=stats["most_recommended_activity"],
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d")
        )

    def get_recommendation_by_id(
        self, 
        recommendation_id: str, 
        user_id: str
    ) -> RecommendationOut:
        """Récupérer une recommandation par ID avec vérification de propriété"""
        recommendation = self.recommendation_repository.get_recommendation_by_id(recommendation_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommandation non trouvée"
            )
        
        if recommendation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cette recommandation"
            )
        
        return RecommendationOut.model_validate(recommendation)

    def get_pending_feedback_recommendations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[RecommendationOut]:
        """Récupérer les recommandations en attente de feedback"""
        recommendations = self.recommendation_repository.get_pending_feedback_recommendations(
            user_id, limit
        )
        return [RecommendationOut.model_validate(r) for r in recommendations]

    def get_feedback_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtenir un résumé des feedbacks utilisateur"""
        recommendations = self.recommendation_repository.get_user_recommendations(user_id, 0, 1000)
        
        # Filtrer par période
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        recent_recommendations = [
            r for r in recommendations 
            if r.timestamp >= start_date and r.was_helpful is not None
        ]
        
        if not recent_recommendations:
            return {
                "total_feedback": 0,
                "helpful_rate": 0.0,
                "most_helpful_activities": [],
                "least_helpful_activities": [],
                "feedback_trends": []
            }
        
        helpful_count = len([r for r in recent_recommendations if r.was_helpful])
        helpful_rate = (helpful_count / len(recent_recommendations)) * 100
        
        # Analyser les activités les plus/moins utiles
        activity_feedback = {}
        for reco in recent_recommendations:
            activity = reco.suggested_activity
            if activity not in activity_feedback:
                activity_feedback[activity] = {"helpful": 0, "total": 0}
            
            activity_feedback[activity]["total"] += 1
            if reco.was_helpful:
                activity_feedback[activity]["helpful"] += 1
        
        # Calculer les taux d'efficacité
        activity_rates = []
        for activity, stats in activity_feedback.items():
            if stats["total"] >= 2:  # Minimum 2 feedbacks
                rate = (stats["helpful"] / stats["total"]) * 100
                activity_rates.append({
                    "activity": activity,
                    "rate": rate,
                    "total_feedback": stats["total"]
                })
        
        activity_rates.sort(key=lambda x: x["rate"], reverse=True)
        
        return {
            "total_feedback": len(recent_recommendations),
            "helpful_rate": round(helpful_rate, 1),
            "most_helpful_activities": activity_rates[:3],
            "least_helpful_activities": activity_rates[-3:] if len(activity_rates) > 3 else [],
            "feedback_trends": self._calculate_feedback_trends(recent_recommendations)
        }

    def _calculate_feedback_trends(self, recommendations: List) -> List[Dict]:
        """Calculer les tendances de feedback par semaine"""
        # Grouper par semaine
        weekly_feedback = {}
        for reco in recommendations:
            week_start = reco.timestamp.date() - timedelta(days=reco.timestamp.weekday())
            week_key = week_start.strftime("%Y-%m-%d")
            
            if week_key not in weekly_feedback:
                weekly_feedback[week_key] = {"helpful": 0, "total": 0}
            
            weekly_feedback[week_key]["total"] += 1
            if reco.was_helpful:
                weekly_feedback[week_key]["helpful"] += 1
        
        # Convertir en liste triée
        trends = []
        for week, stats in sorted(weekly_feedback.items()):
            rate = (stats["helpful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            trends.append({
                "week": week,
                "helpful_rate": round(rate, 1),
                "total_feedback": stats["total"]
            })
        
        return trends

    def get_helpful_recommendations(
        self, 
        user_id: str, 
        days: int = 30, 
        limit: int = 10
    ) -> List[RecommendationOut]:
        """Récupérer les recommandations utiles"""
        recommendations = self.recommendation_repository.get_recommendations_with_feedback(
            user_id, helpful=True, days=days
        )
        return [RecommendationOut.model_validate(r) for r in recommendations[:limit]]

    def get_not_helpful_recommendations(
        self, 
        user_id: str, 
        days: int = 30, 
        limit: int = 10
    ) -> List[RecommendationOut]:
        """Récupérer les recommandations non utiles"""
        recommendations = self.recommendation_repository.get_recommendations_with_feedback(
            user_id, helpful=False, days=days
        )
        return [RecommendationOut.model_validate(r) for r in recommendations[:limit]]

    def analyze_feedback_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyser les patterns de feedback pour améliorer les recommandations futures"""
        feedback_stats = self.recommendation_repository.get_activity_feedback_stats(user_id, 90)
        
        patterns = {
            "preferred_activities": [],
            "avoided_activities": [],
            "time_patterns": {},
            "mood_correlations": {},
            "recommendations": []
        }
        
        # Identifier les activités préférées (taux d'utilité > 70%)
        for activity, stats in feedback_stats.items():
            if stats["total"] >= 3:
                helpfulness_rate = stats["helpful"] / stats["total"]
                
                if helpfulness_rate >= 0.7:
                    patterns["preferred_activities"].append({
                        "activity": activity,
                        "rate": round(helpfulness_rate * 100, 1),
                        "count": stats["total"]
                    })
                elif helpfulness_rate <= 0.3:
                    patterns["avoided_activities"].append({
                        "activity": activity,
                        "rate": round(helpfulness_rate * 100, 1),
                        "count": stats["total"]
                    })
        
        # Générer des recommandations d'amélioration
        if len(patterns["preferred_activities"]) > 0:
            patterns["recommendations"].append(
                "Privilégier les activités créatives et sociales qui semblent vous convenir"
            )
        
        if len(patterns["avoided_activities"]) > 0:
            patterns["recommendations"].append(
                "Éviter temporairement les activités physiques intenses en période de stress"
            )
        
        return patterns
