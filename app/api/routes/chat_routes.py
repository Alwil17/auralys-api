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

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """Dependency injection pour ChatService"""
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
    """Envoyer un message et recevoir une réponse du bot"""
    return chat_service.send_message(current_user, message_data)


@router.get("/history", response_model=ChatConversationOut)
async def get_chat_history(
    skip: int = Query(0, ge=0, description="Nombre de messages à ignorer"),
    limit: int = Query(
        50, ge=1, le=100, description="Nombre max de messages à retourner"
    ),
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Récupérer l'historique de conversation de l'utilisateur"""
    if start_date and end_date:
        return chat_service.get_chat_history_by_date_range(
            str(current_user.id), start_date, end_date
        )
    else:
        return chat_service.get_chat_history(str(current_user.id), skip, limit)


@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    days: int = Query(
        7, ge=1, le=365, description="Nombre de jours pour les statistiques"
    ),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Obtenir les statistiques de chat de l'utilisateur"""
    return chat_service.get_chat_stats(str(current_user.id), days)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_history(
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Supprimer tout l'historique de chat (RGPD)"""
    success = chat_service.delete_user_chat_history(str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun historique de chat trouvé",
        )


@router.get("/nlp/info")
async def get_nlp_model_info():
    """Obtenir des informations sur le modèle NLP"""
    nlp_service = get_nlp_service()
    return nlp_service.get_model_info()


@router.post("/nlp/analyze")
async def analyze_text_emotion(
    text: str, current_user: User = Depends(get_current_user)
):
    """Analyser l'émotion d'un texte (endpoint de test)"""
    nlp_service = get_nlp_service()
    return nlp_service.analyze_emotion(text)
