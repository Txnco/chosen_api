from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DayRatingBase(BaseModel):
    user_id: int = Field(..., description="User ID")
    score: Optional[int] = Field(None, ge=0, le=255, description="Day rating score (0-255)")
    note: Optional[str] = Field(None, max_length=65535, description="Optional note about the day")


class DayRatingCreate(DayRatingBase):
    """Schema for creating a new day rating"""
    pass


class DayRatingUpdate(BaseModel):
    """Schema for updating an existing day rating"""
    score: Optional[int] = Field(None, ge=0, le=255, description="Day rating score (0-255)")
    note: Optional[str] = Field(None, max_length=65535, description="Optional note about the day")


class DayRatingResponse(DayRatingBase):
    """Schema for day rating response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime