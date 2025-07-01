from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime


class UserCreateDTO(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    password: str
    role: Optional[str] = None
    image_url: Optional[str] = None
    consent: Optional[int] = 1


class UserUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None
    consent: Optional[int] = 1


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Optional[str]
    consent: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserExportData(BaseModel):
    """Complete user data export for GDPR compliance"""

    user_info: UserResponse
    mood_entries: List[Dict]
    chat_history: List[Dict]
    recommendations: List[Dict]
    export_timestamp: datetime
    data_retention_period: str


class AccountDeletionRequest(BaseModel):
    """Request to delete user account"""

    confirmation_text: str = Field(
        ..., description="User must type 'DELETE' to confirm"
    )
    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for deletion"
    )


class AccountDeletionResponse(BaseModel):
    """Response after account deletion"""

    message: str
    deletion_timestamp: datetime
    data_anonymized: bool
    backup_retention_days: int
