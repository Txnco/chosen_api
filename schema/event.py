from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class RepeatTypeEnum(str, Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, max_length=5000, description="Event description")
    start_time: datetime = Field(..., description="Event start time (UTC)")
    end_time: datetime = Field(..., description="Event end time (UTC)")
    all_day: bool = Field(default=False, description="Whether event is all-day")
    repeat_type: RepeatTypeEnum = Field(default=RepeatTypeEnum.none, description="Repeat frequency")
    repeat_until: Optional[datetime] = Field(None, description="End date for repeating events")


class EventCreate(BaseModel):
    user_id: int
    title: str
    description: Optional[str] = ""
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    repeat_type: RepeatTypeEnum = RepeatTypeEnum.none
    repeat_until: Optional[datetime] = None

    @field_validator('repeat_until', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('End time must be after start time')
        return v


class EventUpdate(BaseModel):
    """Schema for updating an existing event - all fields optional"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, max_length=5000, description="Event description")
    start_time: Optional[datetime] = Field(None, description="Event start time (UTC)")
    end_time: Optional[datetime] = Field(None, description="Event end time (UTC)")
    all_day: Optional[bool] = Field(None, description="Whether event is all-day")
    repeat_type: Optional[RepeatTypeEnum] = Field(None, description="Repeat frequency")
    repeat_until: Optional[datetime] = Field(None, description="End date for repeating events")


class EventResponse(EventBase):
    """Schema for event response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_repeat_instance: Optional[bool] = None  # Add this field
    original_start: Optional[datetime] = None  # Add this field


class EventWithUser(EventResponse):
    """Schema for event with user details"""
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None


class EventCopyCreate(BaseModel):
    """Schema for copying an event"""
    target_user_id: int = Field(..., description="User ID to copy event to")
    target_date: datetime = Field(..., description="Date to copy event to")


class EventCopyResponse(BaseModel):
    """Schema for event copy response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    event_id: int
    user_id: int
    date: datetime
    created_at: datetime




class EventListQuery(BaseModel):
    """Schema for event list query parameters"""
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    start_date: Optional[datetime] = Field(None, description="Filter events starting from this date")
    end_date: Optional[datetime] = Field(None, description="Filter events until this date")
    include_repeating: bool = Field(default=True, description="Include repeating event instances")


class EventBulkCopyCreate(BaseModel):
    """Schema for copying event to multiple users/dates"""
    target_user_ids: list[int] = Field(..., min_length=1, description="List of user IDs to copy to")
    target_dates: list[datetime] = Field(..., min_length=1, description="List of dates to copy to")


class EventInDB(EventResponse):
    """Schema for event stored in database"""
    pass