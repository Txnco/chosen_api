from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any

VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

class DailyNotification(BaseModel):
    """Daily notification configuration"""
    enabled: bool = True
    time: str = Field("20:00", pattern=r"^\d{2}:\d{2}$")

class WeeklyNotification(BaseModel):
    """Weekly notification configuration"""
    enabled: bool = True
    day: str = Field("monday", description="Day of the week in lowercase string")
    time: str = Field("09:00", pattern=r"^\d{2}:\d{2}$")

    @field_validator("day", mode="before")
    @classmethod
    def convert_day(cls, v):
        """Convert integer day to string or validate string day"""
        if isinstance(v, int):
            return VALID_DAYS[v - 1] if 1 <= v <= 7 else "monday"
        if isinstance(v, str):
            day_lower = v.lower()
            return day_lower if day_lower in VALID_DAYS else "monday"
        return "monday"

class WaterReminderNotification(BaseModel):
    """Water reminder notification configuration"""
    enabled: bool = True
    interval_hours: int = Field(2, ge=1, le=24)

class BirthdayNotification(BaseModel):
    """Birthday notification configuration"""
    enabled: bool = True
    time: str = Field("09:00", pattern=r"^\d{2}:\d{2}$")
    birthday_date: Optional[str] = None

class NotificationPreferencesUpdate(BaseModel):
    """Update model for notification preferences - all fields optional"""
    daily_planning: Optional[Dict[str, Any]] = None
    day_rating: Optional[Dict[str, Any]] = None
    progress_photo: Optional[Dict[str, Any]] = None
    weight_tracking: Optional[Dict[str, Any]] = None
    water_reminders: Optional[Dict[str, Any]] = None
    birthday: Optional[Dict[str, Any]] = None

    class Config:
        # Allow extra fields for flexibility
        extra = "allow"

class NotificationPreferencesResponse(BaseModel):
    """Response model for notification preferences"""
    user_id: int
    notifications: Dict[str, Any]

    class Config:
        from_attributes = True

def get_default_notification_preferences() -> Dict[str, Any]:
    """Get default notification preferences"""
    return {
        "daily_planning": {"enabled": True, "time": "20:00"},
        "day_rating": {"enabled": True, "time": "20:00"},
        "progress_photo": {"enabled": True, "day": "monday", "time": "09:00"},
        "weight_tracking": {"enabled": True, "day": "monday", "time": "08:00"},
        "water_reminders": {"enabled": True, "interval_hours": 2},
        "birthday": {"enabled": True, "time": "09:00"},
    }