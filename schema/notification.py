from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import time

VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

class DailyNotification(BaseModel):
    enabled: bool = True
    time: str = Field("20:00", pattern=r"^\d{2}:\d{2}$")
    calculated_time: Optional[str] = None  # For dynamic calculation

class WeeklyNotification(BaseModel):
    enabled: bool = True
    day: str = Field("monday", description="Day of the week in lowercase string")
    time: str = Field("09:00", pattern=r"^\d{2}:\d{2}$")
    calculated_time: Optional[str] = None

    @field_validator("day", mode="before")
    @classmethod
    def convert_day(cls, v):
        if isinstance(v, int):
            return VALID_DAYS[v - 1] if 1 <= v <= 7 else "monday"
        if isinstance(v, str):
            day_lower = v.lower()
            return day_lower if day_lower in VALID_DAYS else "monday"
        return "monday"


class MonthlyNotification(BaseModel):
    enabled: bool = True
    day_of_month: int = Field(1, ge=1, le=28, description="Day of month (1-28 to avoid month-end issues)")
    time: str = Field("09:00", pattern=r"^\d{2}:\d{2}$")

class WaterReminderNotification(BaseModel):
    enabled: bool = True
    interval_hours: int = Field(2, ge=1, le=24)
    start_time: Optional[str] = None  # Calculated from wake_up_time + 30min
    end_time: Optional[str] = None    # Calculated from sleep_time - 90min

class BirthdayNotification(BaseModel):
    enabled: bool = True
    time: str = Field("09:00", pattern=r"^\d{2}:\d{2}$")
    birthday_date: Optional[str] = None

class NotificationPreferencesUpdate(BaseModel):
    daily_planning: Optional[Dict[str, Any]] = None
    day_rating: Optional[Dict[str, Any]] = None
    progress_photo: Optional[Dict[str, Any]] = None
    weight_tracking: Optional[Dict[str, Any]] = None
    water_reminders: Optional[Dict[str, Any]] = None
    birthday: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"

class NotificationPreferencesResponse(BaseModel):
    user_id: int
    notifications: Dict[str, Any]

    class Config:
        from_attributes = True

def get_default_notification_preferences(user_created_day: int = 1) -> Dict[str, Any]:
    """
    Get default notification preferences.

    Args:
        user_created_day: Day of month from user creation date (for progress_photo)
    """
    # Clamp day to 1-28 to avoid month-end issues
    photo_day = min(max(user_created_day, 1), 28)

    return {
        "daily_planning": {"enabled": True, "time": "20:00"},
        "day_rating": {"enabled": True, "time": "20:00"},
        "progress_photo": {"enabled": True, "day_of_month": photo_day, "time": "09:00"},
        "weight_tracking": {"enabled": True, "day": "saturday", "time": "08:00"},
        "water_reminders": {"enabled": True, "interval_hours": 2},
        "birthday": {"enabled": True, "time": "09:00"},
    }