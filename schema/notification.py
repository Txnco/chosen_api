from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class NotificationPreference(BaseModel):
    """Schema for a single notification preference"""
    enabled: bool = Field(default=True, description="Whether this notification is enabled")
    time: Optional[str] = Field(default=None, description="Time in HH:mm format (24-hour)")
    day: Optional[str] = Field(default=None, description="Day of week for weekly notifications")
    interval_hours: Optional[int] = Field(default=None, ge=1, le=24, description="Interval in hours for recurring notifications")

    @field_validator('time')
    @classmethod
    def validate_time_format(cls, v):
        """Validate time is in HH:mm format"""
        if v is not None:
            if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', v):
                raise ValueError('Time must be in HH:mm format (24-hour)')
        return v

    @field_validator('day')
    @classmethod
    def validate_day(cls, v):
        """Validate day is a valid weekday"""
        if v is not None:
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if v.lower() not in valid_days:
                raise ValueError(f'Day must be one of: {", ".join(valid_days)}')
            return v.lower()
        return v


class NotificationPreferencesBase(BaseModel):
    """Base schema for notification preferences"""
    daily_planning: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=True, time="20:00"),
        description="Daily planning notification"
    )
    day_rating: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=True, time="20:00"),
        description="Day rating notification"
    )
    progress_photo: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=True, day="monday", time="09:00"),
        description="Weekly progress photo notification"
    )
    weigh_in: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=True, day="monday", time="08:00"),
        description="Weekly weigh-in notification"
    )
    water_intake: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=False, interval_hours=2),
        description="Water intake reminder notification"
    )
    birthday: Optional[NotificationPreference] = Field(
        default=NotificationPreference(enabled=True, time="09:00"),
        description="Birthday notification"
    )


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences (all fields optional)"""
    daily_planning: Optional[NotificationPreference] = None
    day_rating: Optional[NotificationPreference] = None
    progress_photo: Optional[NotificationPreference] = None
    weigh_in: Optional[NotificationPreference] = None
    water_intake: Optional[NotificationPreference] = None
    birthday: Optional[NotificationPreference] = None


class NotificationPreferencesResponse(NotificationPreferencesBase):
    """Schema for notification preferences response"""
    user_id: int = Field(..., description="User ID")

    class Config:
        from_attributes = True


def get_default_notification_preferences() -> dict:
    """
    Returns the default notification preferences as a dictionary
    This is used when initializing preferences for new users
    """
    return {
        "daily_planning": {"enabled": True, "time": "20:00"},
        "day_rating": {"enabled": True, "time": "20:00"},
        "progress_photo": {"enabled": True, "day": "monday", "time": "09:00"},
        "weigh_in": {"enabled": True, "day": "monday", "time": "08:00"},
        "water_intake": {"enabled": False, "interval_hours": 2},
        "birthday": {"enabled": True, "time": "09:00"}
    }
