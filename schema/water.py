from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class WaterGoalBase(BaseModel):
    daily_ml: int = Field(..., gt=0, description="Daily water goal in milliliters")


class WaterGoalCreate(WaterGoalBase):
    """Schema for creating a new water goal"""
    pass


class WaterGoalUpdate(BaseModel):
    """Schema for updating an existing water goal"""
    daily_ml: Optional[int] = Field(None, gt=0, description="Daily water goal in milliliters")


class WaterGoalResponse(WaterGoalBase):
    """Schema for water goal response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class WaterTrackingBase(BaseModel):
    water_intake: int = Field(..., ge=0, description="Water intake in milliliters")


class WaterTrackingCreate(WaterTrackingBase):
    """Schema for creating a new water tracking entry"""
    pass


class WaterTrackingUpdate(BaseModel):
    """Schema for updating an existing water tracking entry"""
    water_intake: Optional[int] = Field(None, ge=0, description="Water intake in milliliters")


class WaterTrackingResponse(WaterTrackingBase):
    """Schema for water tracking response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None