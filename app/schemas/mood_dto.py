from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class MoodEntryBase(BaseModel):
    date: str = Field(..., description="Date au format YYYY-MM-DD")
    mood: int = Field(..., ge=1, le=5, description="Humeur de 1 à 5")
    notes: Optional[str] = Field(None, max_length=500, description="Notes optionnelles")
    activity: Optional[str] = Field(
        None, max_length=100, description="Activité du jour"
    )
    sleep_hours: Optional[float] = Field(
        None, ge=0, le=24, description="Heures de sommeil"
    )
    stress_level: Optional[int] = Field(
        None, ge=1, le=5, description="Niveau de stress de 1 à 5"
    )

    @validator("date")
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Date doit être au format YYYY-MM-DD")


class MoodEntryCreate(MoodEntryBase):
    pass


class MoodEntryUpdate(BaseModel):
    mood: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = Field(None, max_length=500)
    activity: Optional[str] = Field(None, max_length=100)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    stress_level: Optional[int] = Field(None, ge=1, le=5)


class MoodEntryOut(MoodEntryBase):
    id: str
    user_id: str
    collected: bool

    class Config:
        from_attributes = True


class MoodEntryStats(BaseModel):
    average_mood: float
    average_stress: Optional[float]
    average_sleep: Optional[float]
    total_entries: int
    period_start: str
    period_end: str
