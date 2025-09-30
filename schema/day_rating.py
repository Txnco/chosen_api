from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class DayRatingBase(BaseModel):
    score: Optional[int] = Field(None, ge=0, le=255, description="Day rating score (0-255)")
    note: Optional[str] = Field(None, max_length=65535, description="Optional note about the day")

class DayRatingCreate(DayRatingBase):
    """Schema for creating day rating entry"""
    pass

class DayRatingUpdate(DayRatingBase):
    """Schema for updating day rating entry"""
    pass

class DayRatingResponse(DayRatingBase):
    """Schema for day rating response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class DayRatingInDB(DayRatingResponse):
    """Schema for day rating stored in database"""
    pass