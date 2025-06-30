from datetime import datetime, timedelta, timezone
from typing import List, Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.user_dto import UserResponse

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserResponse:
    try:
        payload = jwt.decode(
            token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception

    # On transforme l'entité en schéma de sortie
    return UserResponse.model_validate(user)


def hash_password(password: str) -> str:
    """Hash a password for storing.

    Args:
        password (str): The password to hash

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password (str): The password to verify
        hashed_password (str): The hashed password to compare against

    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def verify_token(token: str):
    """Verify a JWT token and return the username if valid.

    Args:
        token (str): The JWT token to verify

    Returns:
        str: The username if the token is valid, raises credentials_exception otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


def get_current_user_role(token: str = Depends(oauth2_scheme)) -> str:
    """Verify a JWT token and return the role if valid.

    Args:
        token (str): The JWT token to verify

    Returns:
        str: The role if the token is valid, raises HTTPException otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        role: str = payload.get("role")
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Role information not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return role
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_roles: List[str]):
    """
    Requires the user to have one of the given roles to access the route.

    Args:
        required_roles (List[str]): The roles that are required to access the route.

    Returns:
        Callable: A function that will check if the current user has one of the required roles.
    """

    def role_checker(role: str = Depends(get_current_user_role)):
        """
        Checks if the current user's role is within the specified required roles.

        Args:
            role (str): The role of the current user obtained via dependency injection.

        Raises:
            HTTPException: If the user's role is not in the list of required roles,
                        an HTTP 403 Forbidden error is raised.

        Returns:
            str: The role of the user if it is within the required roles.
        """
        if role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )
        return role

    return role_checker


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates an access token for a user.

    Args:
        data (dict): Dictionary containing information to be encoded in the access token.
        expires_delta (Optional[timedelta], optional): Optional timedelta specifying when the access token should expire. Defaults to 15 minutes.

    Returns:
        str: The access token as a JSON Web Token (JWT) string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: int, db: Session):
    # Generate a secure token
    """
    Creates a new refresh token for a user.

    Args:
        user_id (int): The ID of the user to create the token for.
        db (Session): The database session to use for storing the token.

    Returns:
        str: The token string.
    """
    token = secrets.token_hex(32)

    # Set expiration (longer than access token)
    expires_delta = timedelta(days=7)  # Refresh token valid for 7 days
    expires_at = datetime.now(tz=timezone.utc) + expires_delta

    # Store token in database
    token_repo = RefreshTokenRepository(db)
    refresh_token = token_repo.create(user_id, token, expires_at)

    return refresh_token.token


def verify_refresh_token(token: str, db: Session):
    """
    Verify a refresh token.

    Args:
        token (str): The refresh token to verify.
        db (Session): The database session to use for verifying the token.

    Raises:
        HTTPException: If the token is invalid, revoked, or expired.

    Returns:
        int: The ID of the user associated with the refresh token if it is valid.
    """
    token_repo = RefreshTokenRepository(db)
    refresh_token = token_repo.get_by_token(token)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if refresh_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if refresh_token.expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return refresh_token.user_id
