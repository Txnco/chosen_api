from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime, time
from enum import Enum

class WorkoutEnvironmentEnum(str, Enum):
    gym = "gym"
    home = "home"
    outdoor = "outdoor"
    both = "both"

class WorkShiftEnum(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    night = "night"
    split = "split"
    flexible = "flexible"

class QuestionnaireBase(BaseModel):
    # numbers
    weight: Optional[float] = Field(None, ge=0, le=1000, description="Weight in kg")
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")

    # dates/times (correct types)
    birthday: Optional[date] = Field(None, description="Birth date (YYYY-MM-DD)")
    wake_up_time: Optional[time] = Field(None, description="Wake up time")
    sleep_time: Optional[time] = Field(None, description="Sleep time")

    # enums / text
    health_issues: Optional[str] = Field(None, max_length=1000, description="Health issues description")
    bad_habits: Optional[str] = Field(None, max_length=1000, description="Bad habits description")
    workout_environment: Optional[WorkoutEnvironmentEnum] = Field(None, description="Preferred workout environment")
    work_shift: Optional[WorkShiftEnum] = Field(None, description="Work shift type")
    morning_routine: Optional[str] = Field(None, max_length=1000, description="Morning routine description")
    evening_routine: Optional[str] = Field(None, max_length=1000, description="Evening routine description")

    # ---------- coercion validators ----------
    @field_validator("birthday", mode="before")
    @classmethod
    def coerce_birthday(cls, v):
        # Accept "2005-09-10T00:00:00.000" or "2005-09-10"
        if isinstance(v, str) and "T" in v:
            return datetime.fromisoformat(v).date()
        if isinstance(v, datetime):
            return v.date()
        return v

    @field_validator("wake_up_time", "sleep_time", mode="before")
    @classmethod
    def coerce_time(cls, v):
        # Accept "06:50" style strings
        if isinstance(v, str):
            return time.fromisoformat(v)
        return v

    @field_validator("birthday")
    @classmethod
    def birthday_not_in_future(cls, v: Optional[date]):
        if v and v > date.today():
            raise ValueError("Birthday cannot be in the future")
        # Optional: ensure not ridiculously old
        # if v and v < date(1900, 1, 1):
        #     raise ValueError("Birthday too old")
        return v

class QuestionnaireCreate(QuestionnaireBase):
    """Schema for creating a new questionnaire"""
    pass

class QuestionnaireUpdate(QuestionnaireBase):
    """Schema for updating an existing questionnaire"""
    pass

class QuestionnaireResponse(QuestionnaireBase):
    """Schema for questionnaire response"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class QuestionnaireInDB(QuestionnaireResponse):
    """Schema for questionnaire stored in database"""
    pass
