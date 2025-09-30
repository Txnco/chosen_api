from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime, date as dt_date
from decimal import Decimal

class WeightTrackingBase(BaseModel):
    weight: Decimal = Field(..., gt=0, le=1000, description="Weight in kg")
    date: Optional[dt_date] = Field(
        None,
        description="Date for this weight entry (defaults to today if omitted)"
    )

class WeightTrackingCreate(WeightTrackingBase):
    @model_validator(mode="before")
    def default_date(cls, values):
        if values.get("date") is None:
            values["date"] = dt_date.today()
        return values

class WeightTrackingUpdate(BaseModel):
    weight: Optional[Decimal] = Field(None, gt=0, le=1000, description="Weight in kg")
    date: Optional[dt_date] = Field(
        None,
        description="Updated date for this weight entry"
    )

class WeightTrackingResponse(WeightTrackingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None