from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime, date


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
