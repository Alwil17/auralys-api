from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.schemas.user_dto import UserCreateDTO, UserResponse, UserUpdateDTO
from app.schemas.auth_dto import TokenResponse, RefreshTokenRequest
from app.services.user_service import UserService
from app.repositories.refresh_token_repository import RefreshTokenRepository
import secrets

from app.db.base import get_db
from sqlalchemy.orm import Session
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserResponse:
    """
    Dependency to get the currently authenticated user from a JWT token
    It extracts the token from the Authorization header, verifies it, and
    then uses the sub (email) claim to find the associated user in the database

    Args:
        token (str, optional): The JWT' token.
        db (Session, optional): The database session.

    Raises:
        HTTPException: If the token is invalid or the user is not found

    Returns:
        UserResponse: The currently authenticated user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = UserService(db).get_user_by_email(email)
    if not user:
        raise credentials_exception

    # On transforme l'entité en schéma de sortie
    return UserResponse.model_validate(user)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a JSON Web Token (JWT) access token.

    Args:
        data (dict): A dictionary containing the payload data
            to encode into the token.
        expires_delta (Optional[timedelta], optional):
            The duration for which the token is valid.
            If None, a default expiration time from settings is used.

    Returns:
        str: The encoded JWT access token as a string.
    """
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: int, db: Session):
    """
    Create a new refresh token for a user.

    Args:
        user_id (int): The ID of the user associated with the refresh token.
        db (Session): The database session to use for storing the token.

    Returns:
        str: The newly created refresh token string.
    """
    token = secrets.token_hex(32)

    # Set expiration (longer than access token)
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expires_at = datetime.now() + expires_delta

    # Store token in database
    token_repo = RefreshTokenRepository(db)
    refresh_token = token_repo.create(user_id, token, expires_at)

    return refresh_token.token


def verify_refresh_token(token: str, db: Session):
    """
    Verify the validity of a refresh token.

    This function checks whether a given refresh token is valid,
        not revoked, and not expired.
    If the token is invalid, revoked, or expired, an HTTPException
        is raised with a 401 status code.

    Args:
        token (str): The refresh token to verify.
        db (Session): The database session used
            to access the refresh token repository.

    Raises:
        HTTPException: If the token is invalid, revoked, or expired.

    Returns:
        int: The user ID associated with the valid refresh token.
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

    if refresh_token.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return refresh_token.user_id


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login to obtain an access token and a refresh token.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the username and password.
        db (Session): The database session.

    Returns:
        TokenResponse: A response containing both an access token and a refresh token.

    Raises:
        HTTPException: If the username or password is incorrect.
    """
    user = UserService(db).authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}
    )

    # Create refresh token
    refresh_token = create_refresh_token(user.id, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access and refresh tokens using a valid refresh token.

    This endpoint allows a user to obtain a new access token and a new refresh token
    by providing a valid refresh token. The old refresh token is revoked, and new tokens
    are issued if the provided refresh token is valid, not revoked, and not expired.

    Args:
        token_data (RefreshTokenRequest): An object containing the refresh token.
        db (Session): The database session used to access the refresh
            token repository and user service.

    Raises:
        HTTPException: If the refresh token is invalid, revoked, expired, or associated user is not found.

    Returns:
        TokenResponse: A response containing the new access token, refresh token, and token type.
    """
    try:
        # Verify the refresh token
        user_id = verify_refresh_token(token_data.refresh_token, db)

        # Get the user
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke the old token
        token_repo = RefreshTokenRepository(db)
        token_repo.revoke(token_data.refresh_token)

        # Generate new tokens
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role, "user_id": user.id}
        )

        new_refresh_token = create_refresh_token(user.id, db)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=204)
async def logout(token_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Revoke a refresh token, effectively logging the user out.

    Args:
        token_data (RefreshTokenRequest): The refresh token to be revoked.
        db (Session): The database session.

    Returns:
        None
    """

    token_repo = RefreshTokenRepository(db)
    token_repo.revoke(token_data.refresh_token)
    return None


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(user_data: UserCreateDTO, db: Session = Depends(get_db)):
    """
    Register a new user

    Args:
        user_data (UserCreateDTO): The user data to be registered.

    Raises:
        HTTPException: If the user already exists or if there is a server error.

    Returns:
        UserResponse: The newly created user object.
    """
    user_service = UserService(db)
    try:
        # Pour les environnements de test, permettre la création d'admins par email
        if (settings.APP_ENV.lower() == "testing") and "admin" in user_data.email:
            user_data.role = "admin"
        else:
            user_data.role = "user"  # Default role for normal users

        user = user_service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return user


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: UserResponse = Depends(get_current_user)):
    """
    Return the current user based on the authentication token.

    This endpoint returns the user object associated with the authentication token provided in the Authorization header.
    The user object is the same as the one returned by the /register endpoint.

    Args:
        current_user (UserResponse): The current user obtained via the get_current_user dependency.

    Returns:
        UserResponse: The current user object.
    """
    return current_user


@router.put("/edit", response_model=UserResponse)
async def edit_current_user(
    update_data: UserUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Edit the current user

    Args:
        update_data (UserUpdateDTO): The data to update the user with.
        db (Session): The database session.
        current_user (UserResponse): The current user obtained via the get_current_user dependency.

    Raises:
        HTTPException: If the user is not found.

    Returns:
        UserResponse: The updated user object.
    """
    user_service = UserService(db)
    updated_user = user_service.update_user(current_user.id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.delete("/remove", status_code=204)
async def remove_current_user(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete the current user.

    Args:
        db (Session): The database session.
        current_user (UserResponse): The current user obtained via the get_current_user dependency.

    Returns:
        None: The user has been successfully deleted.
    """
    user_service = UserService(db)
    user_service.delete_user(current_user.id)
    return None
