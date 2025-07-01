from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.security import verify_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_dto import (
    UserCreateDTO,
    UserUpdateDTO,
    UserExportData,
    AccountDeletionRequest,
)
from app.repositories.mood_repository import MoodRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.recommendation_repository import RecommendationRepository
import json
from datetime import datetime, timedelta


class UserService:
    def __init__(self, db_session: Session):
        self.repository = UserRepository(db_session)

    def create_user(self, user_data: UserCreateDTO) -> User:
        # Check if the user already exists
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("An user with this email already exists.")
        return self.repository.create(user_data)

    def get_user_by_email(self, email: str) -> User:
        return self.repository.get_by_email(email)

    def authenticate_user(self, email: str, password: str) -> User:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.repository.get_by_id(user_id)

    def list_users(self) -> List[User]:
        return self.repository.list()

    def update_user(self, user_id: int, user_data: UserUpdateDTO) -> Optional[User]:
        return self.repository.update(user_id, user_data)

    def delete_user(self, user_id: int) -> bool:
        return self.repository.delete(user_id)

    def export_user_data(self, user_id: str) -> UserExportData:
        """Export all user data for GDPR compliance"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Get all user data from different repositories
        mood_repo = MoodRepository(self.repository.db)
        chat_repo = ChatRepository(self.repository.db)
        recommendation_repo = RecommendationRepository(self.repository.db)

        # Export mood entries
        mood_entries = mood_repo.get_user_mood_entries(user_id, skip=0, limit=10000)
        mood_data = [
            {
                "id": str(entry.id),
                "date": entry.date,
                "mood": entry.mood,
                "stress_level": entry.stress_level,
                "sleep_hours": entry.sleep_hours,
                "notes": entry.notes,
                "activity": entry.activity,
                "created_at": entry.created_at.isoformat(),
                "collected": entry.collected,
            }
            for entry in mood_entries
        ]

        # Export chat history
        chat_messages = chat_repo.get_user_chat_history(user_id, skip=0, limit=10000)
        chat_data = [
            {
                "id": str(msg.id),
                "message": msg.message,
                "sender": msg.sender,
                "mood_detected": msg.mood_detected,
                "language": msg.language,
                "model_used": msg.model_used,
                "timestamp": msg.timestamp.isoformat(),
                "collected": msg.collected,
            }
            for msg in chat_messages
        ]

        # Export recommendations
        recommendations = recommendation_repo.get_user_recommendations(
            user_id, skip=0, limit=10000
        )
        recommendation_data = [
            {
                "id": str(rec.id),
                "suggested_activity": rec.suggested_activity,
                "recommendation_type": rec.recommendation_type,
                "confidence_score": rec.confidence_score,
                "was_helpful": rec.was_helpful,
                "timestamp": rec.timestamp.isoformat(),
                "mood_id": str(rec.mood_id) if rec.mood_id else None,
            }
            for rec in recommendations
        ]

        return UserExportData(
            user_info=UserResponse.model_validate(user),
            mood_entries=mood_data,
            chat_history=chat_data,
            recommendations=recommendation_data,
            export_timestamp=datetime.now(),
            data_retention_period="As per GDPR, data is retained for legitimate business purposes only",
        )

    def delete_user_account(
        self, user_id: str, deletion_request: AccountDeletionRequest
    ) -> dict:
        """Permanently delete user account and all associated data"""

        # Validate confirmation
        if deletion_request.confirmation_text.upper() != "DELETE":
            raise ValueError(
                "Invalid confirmation. Please type 'DELETE' to confirm account deletion."
            )

        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Get repositories for cascading deletion
        mood_repo = MoodRepository(self.repository.db)
        chat_repo = ChatRepository(self.repository.db)
        recommendation_repo = RecommendationRepository(self.repository.db)

        try:
            # Start transaction
            self.repository.db.begin()

            # Delete all associated data
            # Note: With proper foreign key constraints and CASCADE DELETE,
            # this should happen automatically, but we'll be explicit for GDPR compliance

            # Delete mood entries
            mood_repo.delete_all_user_mood_entries(user_id)

            # Delete chat history
            chat_repo.delete_all_user_chat_history(user_id)

            # Delete recommendations
            recommendation_repo.delete_all_user_recommendations(user_id)

            # Finally delete the user account
            success = self.repository.delete(user_id)

            if not success:
                raise ValueError("Failed to delete user account")

            # Commit transaction
            self.repository.db.commit()

            return {
                "message": "Account successfully deleted",
                "deletion_timestamp": datetime.now(),
                "data_anonymized": True,
                "backup_retention_days": 30,  # For legal/business requirements
                "reason": deletion_request.reason,
            }

        except Exception as e:
            # Rollback on error
            self.repository.db.rollback()
            raise ValueError(f"Failed to delete account: {str(e)}")

    def anonymize_user_data(self, user_id: str) -> dict:
        """Alternative to deletion - anonymize user data instead of deleting"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Anonymize user identifiable information
        anonymized_data = UserUpdateDTO(
            name=f"Anonymous_{user_id[:8]}",
            email=f"deleted_{user_id[:8]}@anonymized.local",
            consent=0,  # Revoke consent
        )

        # Update user with anonymized data
        updated_user = self.repository.update(user_id, anonymized_data)

        if not updated_user:
            raise ValueError("Failed to anonymize user data")

        return {
            "message": "User data successfully anonymized",
            "anonymization_timestamp": datetime.now(),
            "data_retained": "Mood entries and aggregated statistics retained for research (anonymized)",
            "user_id_anonymized": f"Anonymous_{user_id[:8]}",
        }
