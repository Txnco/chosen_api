from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class WeightTrackingBase(BaseModel):
    user_id: int = Field(..., description="User ID")
    weight: Decimal = Field(..., gt=0, description="Weight in kg")


class WeightTrackingCreate(WeightTrackingBase):
    """Schema for creating a new weight tracking entry"""
    pass


class WeightTrackingUpdate(BaseModel):
    """Schema for updating an existing weight tracking entry"""
    weight: Optional[Decimal] = Field(None, gt=0, description="Weight in kg")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")


class WeightTrackingResponse(WeightTrackingBase):
    """Schema for weight tracking response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None