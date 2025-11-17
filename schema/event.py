# schema/event.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from models.event import RepeatTypeEnum, RepeatEndTypeEnum, ExceptionTypeEnum


class EventCreate(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    repeat_type: RepeatTypeEnum = RepeatTypeEnum.none
    repeat_interval: int = Field(default=1, ge=1)
    repeat_days: Optional[str] = None
    repeat_until: Optional[datetime] = None
    repeat_end_type: RepeatEndTypeEnum = RepeatEndTypeEnum.never
    repeat_count: Optional[int] = Field(default=None, ge=1)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    repeat_type: Optional[RepeatTypeEnum] = None
    repeat_interval: Optional[int] = Field(None, ge=1)
    repeat_days: Optional[str] = None
    repeat_until: Optional[datetime] = None
    repeat_end_type: Optional[RepeatEndTypeEnum] = None
    repeat_count: Optional[int] = Field(None, ge=1)


class EventResponse(BaseModel):
    id: int
    user_id: int
    parent_event_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool
    repeat_type: str
    repeat_interval: int
    repeat_days: Optional[str] = None
    repeat_until: Optional[datetime] = None
    repeat_end_type: str
    repeat_count: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_repeat_instance: Optional[bool] = None
    original_start: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventWithUser(EventResponse):
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None


class EventCopyCreate(BaseModel):
    target_user_id: int
    target_date: datetime


class EventCopyResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventBulkCopyCreate(BaseModel):
    target_user_ids: List[int]
    target_dates: List[datetime]


class EventExceptionResponse(BaseModel):
    id: int
    event_id: int
    exception_date: datetime
    exception_type: str
    modified_event_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventEditScope(BaseModel):
    scope: str = Field(..., pattern="^(this|future|all)$")
    occurrence_date: Optional[datetime] = None