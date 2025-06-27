from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        """
        Constructor for RefreshTokenRepository

        Args:
            db (Session): The database session
        """
        self.db = db

    def create(self, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
        """
        Create a new refresh token for a user.

        Args:
            user_id (int): The ID of the user associated with the refresh token.
            token (str): The token string.
            expires_at (datetime): The expiration date and time of the token.

        Returns:
            RefreshToken: The newly created refresh token object.
        """
        refresh_token = RefreshToken(
            token=token, user_id=user_id, expires_at=expires_at
        )

        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)

        return refresh_token

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get a refresh token by its value"""
        return self.db.query(RefreshToken).filter(RefreshToken.token == token).first()

    def revoke(self, token: str) -> bool:
        """
        Revoke a refresh token by setting its revoked flag to True.

        Args:
            token (str): The token string to be revoked.

        Returns:
            bool: True if the token was found and revoked, False otherwise.
        """
        refresh_token = self.get_by_token(token)

        if not refresh_token:
            return False

        refresh_token.revoked = True
        self.db.commit()

        return True
