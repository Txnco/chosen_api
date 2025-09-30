from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum

class PhotoAngleEnum(str, Enum):
    front = "front"
    side = "side"
    back = "back"

class ProgressPhotoBase(BaseModel):
    angle: PhotoAngleEnum = Field(..., description="Photo angle (front, side, back)")
    image_url: str = Field(..., max_length=255, description="URL of the progress photo")

class ProgressPhotoCreate(ProgressPhotoBase):
    """Schema for creating progress photo entry"""
    pass

class ProgressPhotoUpdate(BaseModel):
    """Schema for updating progress photo entry"""
    angle: Optional[PhotoAngleEnum] = Field(None, description="Photo angle (front, side, back)")
    image_url: Optional[str] = Field(None, max_length=255, description="URL of the progress photo")

class ProgressPhotoResponse(ProgressPhotoBase):
    """Schema for progress photo response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

class ProgressPhotoInDB(ProgressPhotoResponse):
    """Schema for progress photo stored in database"""
    pass