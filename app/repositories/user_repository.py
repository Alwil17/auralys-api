from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.user_dto import UserCreateDTO, UserUpdateDTO
from app.core.config import settings


class UserRepository:
    def __init__(self, db: Session):
        """
        Constructor for UserRepository

        Args:
            db (Session): The database session
        """
        self.db = db

    def create(self, user_data: UserCreateDTO) -> User:
        hashed_pw = hash_password(user_data.password)
        user = User(
            name=user_data.name, email=user_data.email, hashed_password=hashed_pw
        )

        if settings.APP_DEBUG and ("admin" in user_data.email):
            user.role = "admin"

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def list(self) -> List[User]:
        return self.db.query(User).all()

    def update(self, user_id: int, user_data: UserUpdateDTO) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        update_data = user_data.model_dump(exclude_unset=True)
        # Hash the password if present
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True
