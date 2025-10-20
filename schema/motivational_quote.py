
"""
==============================================================================
File 2 of 3: schema/motivational_quote.py
Copy this entire file to your schema folder
==============================================================================
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MotivationalQuoteBase(BaseModel):
    quote: str = Field(..., min_length=1, description="The motivational quote text")
    author: Optional[str] = Field(None, max_length=255, description="Quote author")
    is_active: bool = Field(default=True, description="Whether quote is active")


class MotivationalQuoteCreate(MotivationalQuoteBase):
    """Schema for creating a new motivational quote"""
    pass


class MotivationalQuoteUpdate(BaseModel):
    """Schema for updating an existing motivational quote"""
    quote: Optional[str] = Field(None, min_length=1, description="The motivational quote text")
    author: Optional[str] = Field(None, max_length=255, description="Quote author")
    is_active: Optional[bool] = Field(None, description="Whether quote is active")


class MotivationalQuoteResponse(MotivationalQuoteBase):
    """Schema for motivational quote response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    times_shown: int
    last_shown_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class MotivationalQuoteInDB(MotivationalQuoteResponse):
    """Schema for motivational quote stored in database"""
    pass


class RandomQuoteResponse(BaseModel):
    """Schema for random quote endpoint response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    quote: str
    author: Optional[str] = None
    times_shown: int

