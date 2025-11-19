# schema/questionnaire.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime, time
from enum import Enum

class WorkoutEnvironmentEnum(str, Enum):
    gym = "gym"
    home = "home"
    outdoor = "outdoor"

class ShiftTypeEnum(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    night = "night"
    split = "split"
    flexible = "flexible"

class WorkShift(BaseModel):
    type: ShiftTypeEnum
    start: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    end: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    start2: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    end2: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    break_time: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')

class QuestionnaireBase(BaseModel):
    weight: Optional[float] = Field(None, ge=0, le=1000)
    height: Optional[float] = Field(None, ge=0, le=300)
    birthday: Optional[date] = None
    health_issues: Optional[str] = Field(None, max_length=1000)
    bad_habits: Optional[str] = Field(None, max_length=1000)
    workout_environment: Optional[str] = None
    work_shifts: Optional[List[WorkShift]] = Field(default_factory=list)
    wake_up_time: Optional[time] = None
    sleep_time: Optional[time] = None
    morning_routine: Optional[str] = Field(None, max_length=1000)
    evening_routine: Optional[str] = Field(None, max_length=1000)

    @field_validator("birthday", mode="before")
    @classmethod
    def coerce_birthday(cls, v):
        if isinstance(v, str):
            if "T" in v:
                return datetime.fromisoformat(v.split('T')[0]).date()
            return date.fromisoformat(v)
        if isinstance(v, datetime):
            return v.date()
        return v

    @field_validator("wake_up_time", "sleep_time", mode="before")
    @classmethod
    def coerce_time(cls, v):
        if isinstance(v, str):
            if "T" in v:
                dt = datetime.fromisoformat(v)
                return time(hour=dt.hour, minute=dt.minute)
            return time.fromisoformat(v)
        return v

    @field_validator("birthday")
    @classmethod
    def birthday_not_in_future(cls, v: Optional[date]):
        if v and v > date.today():
            raise ValueError("Birthday cannot be in the future")
        return v
    
    @field_validator("workout_environment", mode="before")
    @classmethod
    def lowercase_environment(cls, v):
        if v and isinstance(v, str):
            return v.lower()
        return v

class QuestionnaireCreate(QuestionnaireBase):
    pass

class QuestionnaireUpdate(QuestionnaireBase):
    pass

class QuestionnaireResponse(QuestionnaireBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime