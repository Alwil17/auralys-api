from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.base import get_db
from app.repositories.chat_repository import ChatRepository
from app.services.chat_service import ChatService
from app.schemas.chat_dto import (
    ChatMessageCreate,
    ChatBotResponse,
    ChatConversationOut,
    ChatStats,
)
from app.core.security import get_current_user
from app.db.models.user import User
from app.services.nlp_service import get_nlp_service

router = APIRouter(prefix="/chat", tags=["Chat & NLP"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """
    Dependency injection de ChatService, qui nécessite un Session de DB.

    Returns:
        ChatService: instance de ChatService, prête à l'emploi.
    """
    chat_repository = ChatRepository(db)
    return ChatService(chat_repository)


@router.post(
    "/send", response_model=ChatBotResponse, status_code=status.HTTP_201_CREATED
)
async def send_message(
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Send a message to the chat bot and receive a response.

    Args:
        message_data: Message data containing the user's message and language.
        current_user: Connected user, injected by FastAPI via get_current_user.
        chat_service: ChatService instance, injected by FastAPI via get_chat_service.

    Returns:
        ChatBotResponse: The response from the chat bot.
    """
    return chat_service.send_message(current_user, message_data)


@router.get("/history", response_model=ChatConversationOut)
async def get_chat_history(
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of messages to return"
    ),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Retrieve the chat history for the current user.

    Args:
        skip: Number of messages to skip
        limit: Number of messages to return
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        current_user: Connected user, injected by FastAPI via get_current_user
        chat_service: ChatService instance, injected by FastAPI via get_chat_service

    Returns:
        ChatConversationOut: Chat conversation history for the user.
    """
    if start_date and end_date:
        return chat_service.get_chat_history_by_date_range(
            str(current_user.id), start_date, end_date
        )
    else:
        return chat_service.get_chat_history(str(current_user.id), skip, limit)


@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    days: int = Query(
        7, ge=1, le=365, description="Number of days for chat statistics"
    ),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Retrieve chat statistics for the current user over a specified period.

    Args:
        days (int): The number of days for which to retrieve chat statistics.
                    Must be between 1 and 365.
        current_user (User): The authenticated user, injected by FastAPI.
        chat_service (ChatService): The ChatService instance, injected by FastAPI.

    Returns:
        ChatStats: The statistics of the user's chat activity over the specified period.
    """
    return chat_service.get_chat_stats(str(current_user.id), days)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_history(
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Delete the chat history for the current user.

    Args:
        current_user (User): The connected user, injected by FastAPI via get_current_user.
        chat_service (ChatService): ChatService instance, injected by FastAPI via get_chat_service.

    Raises:
        HTTPException: If no chat history is found for the user, with a 404 status code.
    """
    success = chat_service.delete_user_chat_history(str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chat history found for the user",
        )


@router.get("/nlp/info")
async def get_nlp_model_info():
    """
    Get information about the NLP model used for emotion analysis

    Returns:
        Dict: A dictionary containing the model information
    """
    nlp_service = get_nlp_service()
    return nlp_service.get_model_info()


@router.post("/nlp/analyze")
async def analyze_text_emotion(
    text: str, current_user: User = Depends(get_current_user)
):
    """
    Analyze the emotion of a given text

    Args:
        text (str): The text to analyze

    Returns:
        Dict: A dictionary containing the emotion analysis result
    """
    nlp_service = get_nlp_service()
    return nlp_service.analyze_emotion(text)
