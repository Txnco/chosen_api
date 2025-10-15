from pydantic import BaseModel, Field, ConfigDict, field_serializer
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

class ProgressPhotoResponse(BaseModel):
    id: int
    user_id: int
    angle: str
    image_url: str
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('image_url')
    def serialize_image_url(self, image_url: str) -> str:
        # If image_url already contains http, return as is (backward compatibility)
        if image_url and (image_url.startswith('http://') or image_url.startswith('https://')):
            return image_url
        # Otherwise, construct the full URL
        return f"https://admin.chosen-international.com/public/uploads/progress/{image_url}"
    
    model_config = ConfigDict(from_attributes=True)

class ProgressPhotoInDB(ProgressPhotoResponse):
    """Schema for progress photo stored in database"""
    pass