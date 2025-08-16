from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class PhotoAngleEnum(str, Enum):
    front = "front"
    side = "side"
    back = "back"


class ProgressPhotoBase(BaseModel):
    user_id: int = Field(..., description="User ID")
    angle: PhotoAngleEnum = Field(..., description="Photo angle")
    image_url: str = Field(..., max_length=255, description="URL to the progress photo")


class ProgressPhotoCreate(ProgressPhotoBase):
    """Schema for creating a new progress photo"""
    pass


class ProgressPhotoUpdate(BaseModel):
    """Schema for updating an existing progress photo"""
    angle: Optional[PhotoAngleEnum] = Field(None, description="Photo angle")
    image_url: Optional[str] = Field(None, max_length=255, description="URL to the progress photo")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")


class ProgressPhotoResponse(ProgressPhotoBase):
    """Schema for progress photo response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None