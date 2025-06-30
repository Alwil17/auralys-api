from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class ChatMessageBase(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="Contenu du message"
    )
    sender: Literal["user", "bot"] = Field(..., description="Expéditeur du message")
    mood_detected: Optional[str] = Field(
        None, max_length=50, description="Humeur détectée par NLP"
    )


class ChatMessageCreate(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="Message de l'utilisateur"
    )

    @field_validator("message")
    def validate_message_content(cls, v):
        if not v.strip():
            raise ValueError("Le message ne peut pas être vide")
        return v.strip()


class ChatMessageOut(ChatMessageBase):
    id: str
    user_id: str
    timestamp: datetime
    collected: bool

    model_config = ConfigDict(from_attributes=True, extra="allow")


class ChatConversationOut(BaseModel):
    """Représente une conversation complète avec plusieurs messages"""

    messages: list[ChatMessageOut]
    total_messages: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]


class ChatBotResponse(BaseModel):
    """Réponse du chatbot à un message utilisateur"""

    bot_message: str = Field(..., description="Réponse générée par le bot")
    mood_detected: Optional[str] = Field(
        None, description="Humeur détectée dans le message utilisateur"
    )
    suggestions: Optional[list[str]] = Field(
        default_factory=list, description="Suggestions d'activités"
    )


class ChatStats(BaseModel):
    """Statistiques des conversations chat"""

    total_messages: int
    messages_user: int
    messages_bot: int
    most_detected_mood: Optional[str]
    average_messages_per_day: float
    period_start: str
    period_end: str


class ChatMoodAnalysis(BaseModel):
    """Analyse des humeurs détectées dans les conversations"""

    mood: str
    frequency: int
    percentage: float
    last_detected: datetime
