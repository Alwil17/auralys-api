from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.db.models.recommendation import Recommendation
from app.schemas.recommendation_dto import RecommendationCreate, RecommendationUpdate


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_recommendation(
        self, 
        user_id: str, 
        recommendation_data: RecommendationCreate
    ) -> Recommendation:
        """Créer une nouvelle recommandation"""
        db_recommendation = Recommendation(
            user_id=user_id,
            **recommendation_data.model_dump(exclude_unset=True)
        )
        
        self.db.add(db_recommendation)
        self.db.commit()
        self.db.refresh(db_recommendation)
        return db_recommendation

    def get_recommendation_by_id(self, recommendation_id: str) -> Optional[Recommendation]:
        """Récupérer une recommandation par ID"""
        return self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id
        ).first()

    def get_user_recommendations(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[Recommendation]:
        """Récupérer les recommandations d'un utilisateur"""
        return self.db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).order_by(desc(Recommendation.timestamp)).offset(skip).limit(limit).all()

    def get_recommendations_by_mood(
        self, 
        user_id: str, 
        mood_id: str
    ) -> List[Recommendation]:
        """Récupérer les recommandations pour une entrée d'humeur spécifique"""
        return self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.mood_id == mood_id
            )
        ).order_by(desc(Recommendation.timestamp)).all()

    def update_recommendation_feedback(
        self, 
        recommendation_id: str, 
        feedback_data: RecommendationUpdate
    ) -> Optional[Recommendation]:
        """Mettre à jour le feedback d'une recommandation"""
        recommendation = self.get_recommendation_by_id(recommendation_id)
        if recommendation:
            update_data = feedback_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(recommendation, field, value)
            self.db.commit()
            self.db.refresh(recommendation)
        return recommendation

    def get_recent_recommendations(
        self, 
        user_id: str, 
        hours: int = 24
    ) -> List[Recommendation]:
        """Récupérer les recommandations récentes pour éviter les doublons"""
        since = datetime.now() - timedelta(hours=hours)
        return self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.timestamp >= since
            )
        ).all()

    def get_recommendation_stats(self, user_id: str, days: int = 30) -> Dict:
        """Calculer les statistiques de recommandations"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recommendations = self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.timestamp >= start_date
            )
        ).all()
        
        if not recommendations:
            return {
                "total_recommendations": 0,
                "helpful_count": 0,
                "not_helpful_count": 0,
                "pending_feedback": 0,
                "helpfulness_rate": 0.0,
                "most_recommended_activity": None
            }
        
        helpful_count = len([r for r in recommendations if r.was_helpful is True])
        not_helpful_count = len([r for r in recommendations if r.was_helpful is False])
        pending_feedback = len([r for r in recommendations if r.was_helpful is None])
        
        # Calculer le taux d'utilité
        total_with_feedback = helpful_count + not_helpful_count
        helpfulness_rate = (helpful_count / total_with_feedback) if total_with_feedback > 0 else 0.0
        
        # Activité la plus recommandée
        activities = [r.suggested_activity for r in recommendations]
        most_recommended = max(set(activities), key=activities.count) if activities else None
        
        return {
            "total_recommendations": len(recommendations),
            "helpful_count": helpful_count,
            "not_helpful_count": not_helpful_count,
            "pending_feedback": pending_feedback,
            "helpfulness_rate": round(helpfulness_rate, 2),
            "most_recommended_activity": most_recommended
        }

    def delete_user_recommendations(self, user_id: str) -> int:
        """Supprimer toutes les recommandations d'un utilisateur"""
        deleted_count = self.db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).delete()
        self.db.commit()
        return deleted_count

    def get_pending_feedback_recommendations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Recommendation]:
        """Récupérer les recommandations en attente de feedback"""
        return self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.was_helpful.is_(None)
            )
        ).order_by(desc(Recommendation.timestamp)).limit(limit).all()

    def get_recommendations_with_feedback(
        self, 
        user_id: str, 
        helpful: Optional[bool] = None,
        days: int = 30
    ) -> List[Recommendation]:
        """Récupérer les recommandations avec feedback spécifique"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.timestamp >= start_date,
                Recommendation.was_helpful.is_not(None)
            )
        )
        
        if helpful is not None:
            query = query.filter(Recommendation.was_helpful == helpful)
        
        return query.order_by(desc(Recommendation.timestamp)).all()

    def get_activity_feedback_stats(self, user_id: str, days: int = 30) -> Dict:
        """Obtenir les statistiques de feedback par activité"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recommendations = self.db.query(Recommendation).filter(
            and_(
                Recommendation.user_id == user_id,
                Recommendation.timestamp >= start_date,
                Recommendation.was_helpful.is_not(None)
            )
        ).all()
        
        # Analyser par activité
        activity_stats = {}
        for reco in recommendations:
            activity = reco.suggested_activity
            if activity not in activity_stats:
                activity_stats[activity] = {
                    "total": 0,
                    "helpful": 0,
                    "not_helpful": 0,
                    "last_feedback_date": None
                }
            
            activity_stats[activity]["total"] += 1
            if reco.was_helpful:
                activity_stats[activity]["helpful"] += 1
            else:
                activity_stats[activity]["not_helpful"] += 1
            
            # Mettre à jour la date du dernier feedback
            if (activity_stats[activity]["last_feedback_date"] is None or 
                reco.timestamp > activity_stats[activity]["last_feedback_date"]):
                activity_stats[activity]["last_feedback_date"] = reco.timestamp
        
        return activity_stats
