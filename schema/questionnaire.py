from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
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
    weight: Optional[float] = Field(None, ge=0, le=1000, description="Weight in kg")
    height: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")
    birthday: Optional[datetime] = Field(None, ge=0, le=150, description="Birthday in date")
    health_issues: Optional[str] = Field(None, max_length=1000, description="Health issues description")
    bad_habits: Optional[str] = Field(None, max_length=1000, description="Bad habits description")
    workout_environment: Optional[WorkoutEnvironmentEnum] = Field(None, description="Preferred workout environment")
    work_shift: Optional[WorkShiftEnum] = Field(None, description="Work shift type")
    wake_up_time: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Wake up time in HH:MM format")
    sleep_time: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Sleep time in HH:MM format")
    morning_routine: Optional[str] = Field(None, max_length=1000, description="Morning routine description")
    evening_routine: Optional[str] = Field(None, max_length=1000, description="Evening routine description")

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