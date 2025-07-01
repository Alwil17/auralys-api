from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.repositories.mood_repository import MoodRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.stats_dto import (
    UserOverallStats,
    WeeklyMoodTrend,
    MoodDistribution,
    ActivityEffectiveness,
    WellnessInsights,
    DailyMoodEntry,
    PeriodComparison
)


class StatsService:
    def __init__(self, db_session: Session):
        self.mood_repository = MoodRepository(db_session)
        self.chat_repository = ChatRepository(db_session)
        self.recommendation_repository = RecommendationRepository(db_session)

    def get_user_overall_stats(self, user_id: str, days: int = 30) -> UserOverallStats:
        """Obtenir les statistiques générales d'un utilisateur"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Statistiques d'humeur
        mood_stats = self.mood_repository.get_user_mood_stats(user_id, days)
        
        # Statistiques de chat
        chat_stats = self.chat_repository.get_chat_stats(user_id, days)
        
        # Statistiques de recommandations
        reco_stats = self.recommendation_repository.get_recommendation_stats(user_id, days)
        
        # Calculer les insights
        insights = self._generate_wellness_insights(user_id, days)
        
        return UserOverallStats(
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            mood_entries_count=mood_stats["total_entries"],
            average_mood=mood_stats["average_mood"],
            average_sleep=mood_stats["average_sleep"],
            average_stress=mood_stats["average_stress"],
            chat_messages_count=chat_stats["messages_user"],
            recommendations_received=reco_stats["total_recommendations"],
            recommendations_helpful=reco_stats["helpful_count"],
            wellness_score=self._calculate_wellness_score(mood_stats, chat_stats, reco_stats),
            insights=insights
        )

    def get_weekly_mood_trends(self, user_id: str, weeks: int = 4) -> List[WeeklyMoodTrend]:
        """Obtenir les tendances d'humeur par semaine"""
        trends = []
        end_date = datetime.now().date()
        
        for week in range(weeks):
            week_end = end_date - timedelta(weeks=week)
            week_start = week_end - timedelta(days=6)
            
            # Récupérer les entrées de la semaine
            mood_entries = self.mood_repository.get_user_mood_entries_by_date_range(
                user_id, week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")
            )
            
            if mood_entries:
                moods = [entry.mood for entry in mood_entries]
                stress_levels = [entry.stress_level for entry in mood_entries if entry.stress_level]
                sleep_hours = [entry.sleep_hours for entry in mood_entries if entry.sleep_hours]
                
                trend = WeeklyMoodTrend(
                    week_start=week_start.strftime("%Y-%m-%d"),
                    week_end=week_end.strftime("%Y-%m-%d"),
                    entries_count=len(mood_entries),
                    average_mood=round(sum(moods) / len(moods), 2),
                    average_stress=round(sum(stress_levels) / len(stress_levels), 2) if stress_levels else None,
                    average_sleep=round(sum(sleep_hours) / len(sleep_hours), 2) if sleep_hours else None,
                    mood_trend=self._calculate_trend(moods)
                )
            else:
                trend = WeeklyMoodTrend(
                    week_start=week_start.strftime("%Y-%m-%d"),
                    week_end=week_end.strftime("%Y-%m-%d"),
                    entries_count=0,
                    average_mood=0,
                    average_stress=None,
                    average_sleep=None,
                    mood_trend="stable"
                )
            
            trends.append(trend)
        
        return list(reversed(trends))  # Plus ancien en premier

    def get_mood_distribution(self, user_id: str, days: int = 30) -> MoodDistribution:
        """Obtenir la distribution des humeurs"""
        mood_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id, 
            (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )
        
        # Compter les occurrences de chaque niveau d'humeur
        mood_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for entry in mood_entries:
            if entry.mood in mood_counts:
                mood_counts[entry.mood] += 1
        
        total_entries = len(mood_entries)
        
        return MoodDistribution(
            total_entries=total_entries,
            mood_1_count=mood_counts[1],
            mood_2_count=mood_counts[2],
            mood_3_count=mood_counts[3],
            mood_4_count=mood_counts[4],
            mood_5_count=mood_counts[5],
            mood_1_percentage=round((mood_counts[1] / total_entries * 100), 1) if total_entries > 0 else 0,
            mood_2_percentage=round((mood_counts[2] / total_entries * 100), 1) if total_entries > 0 else 0,
            mood_3_percentage=round((mood_counts[3] / total_entries * 100), 1) if total_entries > 0 else 0,
            mood_4_percentage=round((mood_counts[4] / total_entries * 100), 1) if total_entries > 0 else 0,
            mood_5_percentage=round((mood_counts[5] / total_entries * 100), 1) if total_entries > 0 else 0,
            most_common_mood=max(mood_counts, key=mood_counts.get) if total_entries > 0 else None
        )

    def get_activity_effectiveness(self, user_id: str, days: int = 30) -> List[ActivityEffectiveness]:
        """Analyser l'efficacité des activités recommandées"""
        recommendations = self.recommendation_repository.get_user_recommendations(user_id, 0, 1000)
        
        # Filtrer les recommandations avec feedback dans la période
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recent_recommendations = [
            r for r in recommendations 
            if r.timestamp >= start_date and r.was_helpful is not None
        ]
        
        # Grouper par activité
        activity_stats = {}
        for reco in recent_recommendations:
            activity = reco.suggested_activity
            if activity not in activity_stats:
                activity_stats[activity] = {"helpful": 0, "not_helpful": 0, "total": 0}
            
            activity_stats[activity]["total"] += 1
            if reco.was_helpful:
                activity_stats[activity]["helpful"] += 1
            else:
                activity_stats[activity]["not_helpful"] += 1
        
        # Convertir en liste avec calcul d'efficacité
        effectiveness_list = []
        for activity, stats in activity_stats.items():
            if stats["total"] >= 3:  # Minimum 3 essais pour être statistiquement valable
                effectiveness_rate = (stats["helpful"] / stats["total"]) * 100
                effectiveness_list.append(
                    ActivityEffectiveness(
                        activity=activity,
                        times_recommended=stats["total"],
                        times_helpful=stats["helpful"],
                        effectiveness_rate=round(effectiveness_rate, 1)
                    )
                )
        
        # Trier par efficacité
        return sorted(effectiveness_list, key=lambda x: x.effectiveness_rate, reverse=True)

    def get_daily_mood_entries(self, user_id: str, days: int) -> List[DailyMoodEntry]:
        """Obtenir les entrées quotidiennes pour les graphiques"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Récupérer toutes les entrées
        mood_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Créer un dictionnaire des entrées par date
        entries_by_date = {entry.date: entry for entry in mood_entries}
        
        # Créer une liste avec toutes les dates (même celles sans entrée)
        daily_entries = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            entry = entries_by_date.get(date_str)
            
            daily_entries.append(DailyMoodEntry(
                date=date_str,
                mood=entry.mood if entry else None,
                stress=entry.stress_level if entry else None,
                sleep=entry.sleep_hours if entry else None
            ))
            
            current_date += timedelta(days=1)
        
        return daily_entries

    def get_period_comparison(self, user_id: str, days: int) -> Optional[PeriodComparison]:
        """Comparer la période actuelle avec la précédente"""
        end_date = datetime.now().date()
        current_start = end_date - timedelta(days=days-1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days-1)
        
        # Entrées période actuelle
        current_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id,
            current_start.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Entrées période précédente
        previous_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id,
            previous_start.strftime("%Y-%m-%d"),
            previous_end.strftime("%Y-%m-%d")
        )
        
        if not current_entries or not previous_entries:
            return None
        
        # Calculer les moyennes
        current_avg = sum(e.mood for e in current_entries) / len(current_entries)
        previous_avg = sum(e.mood for e in previous_entries) / len(previous_entries)
        
        mood_change = current_avg - previous_avg
        mood_change_percentage = (mood_change / previous_avg) * 100 if previous_avg > 0 else 0
        
        # Déterminer la tendance
        if mood_change >= 0.5:
            trend = "much_better"
        elif mood_change >= 0.2:
            trend = "better"
        elif mood_change <= -0.5:
            trend = "much_worse"
        elif mood_change <= -0.2:
            trend = "worse"
        else:
            trend = "stable"
        
        return PeriodComparison(
            current_period=f"{current_start.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
            previous_period=f"{previous_start.strftime('%Y-%m-%d')} - {previous_end.strftime('%Y-%m-%d')}",
            current_average_mood=round(current_avg, 2),
            previous_average_mood=round(previous_avg, 2),
            mood_change=round(mood_change, 2),
            mood_change_percentage=round(mood_change_percentage, 1),
            trend=trend
        )

    def _calculate_wellness_score(self, mood_stats: Dict, chat_stats: Dict, reco_stats: Dict) -> float:
        """Calculer un score de bien-être global (0-100)"""
        score = 50  # Score de base
        
        # Facteur humeur (40% du score)
        avg_mood = mood_stats.get("average_mood", 0)
        if avg_mood > 0:
            mood_score = (avg_mood - 1) / 4 * 40  # Normaliser 1-5 vers 0-40
            score += mood_score - 20  # Centrer autour de 50
        
        # Facteur régularité (30% du score)
        entries_count = mood_stats.get("total_entries", 0)
        if entries_count >= 20:  # Très régulier
            score += 15
        elif entries_count >= 10:  # Modérément régulier
            score += 10
        elif entries_count >= 5:  # Peu régulier
            score += 5
        
        # Facteur engagement chat (15% du score)
        chat_messages = chat_stats.get("messages_user", 0)
        if chat_messages >= 10:
            score += 7
        elif chat_messages >= 5:
            score += 5
        elif chat_messages >= 1:
            score += 3
        
        # Facteur utilisation recommandations (15% du score)
        helpful_rate = reco_stats.get("helpfulness_rate", 0)
        if helpful_rate >= 0.7:
            score += 8
        elif helpful_rate >= 0.5:
            score += 5
        elif helpful_rate >= 0.3:
            score += 3
        
        return max(0, min(100, round(score, 1)))

    def _calculate_trend(self, moods: List[int]) -> str:
        """Calculer la tendance d'une série d'humeurs"""
        if len(moods) < 2:
            return "stable"
        
        # Calculer la pente de la tendance
        x = list(range(len(moods)))
        n = len(moods)
        sum_x = sum(x)
        sum_y = sum(moods)
        sum_xy = sum(x[i] * moods[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "declining"
        else:
            return "stable"

    def _generate_wellness_insights(self, user_id: str, days: int) -> List[str]:
        """Générer des insights personnalisés"""
        insights = []
        
        # Analyser les patterns d'humeur
        mood_entries = self.mood_repository.get_user_mood_entries_by_date_range(
            user_id,
            (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )
        
        if not mood_entries:
            insights.append("Commencez à enregistrer votre humeur quotidiennement pour obtenir des insights personnalisés.")
            return insights
        
        # Analyser la régularité
        if len(mood_entries) >= days * 0.8:
            insights.append("Excellente régularité dans le suivi de votre humeur ! Continuez ainsi.")
        elif len(mood_entries) >= days * 0.5:
            insights.append("Bon suivi de votre humeur. Essayez d'être encore plus régulier pour de meilleurs insights.")
        else:
            insights.append("Essayez d'enregistrer votre humeur plus régulièrement pour identifier des patterns.")
        
        # Analyser les corrélations sommeil-humeur
        entries_with_sleep = [e for e in mood_entries if hasattr(e, 'sleep_hours') and e.sleep_hours]
        if len(entries_with_sleep) >= 5:
            good_sleep_moods = [e.mood for e in entries_with_sleep if e.sleep_hours >= 7]
            poor_sleep_moods = [e.mood for e in entries_with_sleep if e.sleep_hours < 6]
            
            if good_sleep_moods and poor_sleep_moods:
                good_avg = sum(good_sleep_moods) / len(good_sleep_moods)
                poor_avg = sum(poor_sleep_moods) / len(poor_sleep_moods)
                
                if good_avg - poor_avg > 0.5:
                    insights.append("Votre humeur semble meilleure quand vous dormez bien (7h+). Privilégiez un bon sommeil.")
        
        # Analyser les tendances de stress
        entries_with_stress = [e for e in mood_entries if hasattr(e, 'stress_level') and e.stress_level]
        if entries_with_stress:
            avg_stress = sum(e.stress_level for e in entries_with_stress) / len(entries_with_stress)
            if avg_stress >= 4:
                insights.append("Votre niveau de stress semble élevé. Pensez à intégrer des activités relaxantes dans votre routine.")
            elif avg_stress <= 2:
                insights.append("Votre gestion du stress semble efficace. Continuez vos bonnes habitudes.")
        
        return insights[:3]  # Limiter à 3 insights maximum
