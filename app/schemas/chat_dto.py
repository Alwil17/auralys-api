from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal, Dict
from datetime import datetime


class ChatMessageBase(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="Contenu du message"
    )
    sender: Literal["user", "bot"] = Field(..., description="Expéditeur du message")
    mood_detected: Optional[str] = Field(
        None, max_length=50, description="Humeur détectée par NLP"
    )
    translated_message: Optional[str] = Field(
        None, max_length=2000, description="Message traduit si nécessaire"
    )
    language: Optional[str] = Field(
        None, max_length=10, description="Langue détectée ou imposée (ex: 'fr', 'en')"
    )
    model_used: Optional[str] = Field(
        None,
        max_length=100,
        description="Modèle NLP utilisé (ex: 'distilroberta-emotion-en')",
    )


class ChatMessageCreate(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="Message de l'utilisateur"
    )
    language: Optional[str] = Field(
        None, max_length=10, description="Langue préférée de l'utilisateur"
    )

    @field_validator("message")
    def validate_message_content(cls, v):
        if not v.strip():
            raise ValueError("Le message ne peut pas être vide")
        return v.strip()

    @field_validator("language")
    def validate_language_code(cls, v):
        if v is not None:
            # Valider les codes de langue ISO 639-1
            valid_languages = [
                "fr",
                "en",
                "es",
                "de",
                "it",
                "pt",
                "nl",
                "ru",
                "zh",
                "ja",
                "ar",
            ]
            if v.lower() not in valid_languages:
                raise ValueError(
                    f"Code de langue non supporté. Langues disponibles: {', '.join(valid_languages)}"
                )
            return v.lower()
        return v


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
    emotion_analysis: Optional[Dict] = Field(
        None, description="Analyse détaillée des émotions par le modèle NLP"
    )
    language_detected: Optional[str] = Field(
        None, description="Langue détectée du message utilisateur"
    )
    model_used: Optional[str] = Field(
        None, description="Modèle NLP utilisé pour l'analyse"
    )
    translated_input: Optional[str] = Field(
        None, description="Message traduit si traduction nécessaire"
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


class ChatLanguageStats(BaseModel):
    """Statistiques des langues utilisées dans les conversations"""

    language: str
    message_count: int
    percentage: float
    most_recent_use: datetime


class ChatModelStats(BaseModel):
    """Statistiques des modèles NLP utilisés"""

    model_name: str
    usage_count: int
    accuracy_score: Optional[float] = None
    average_confidence: Optional[float] = None
