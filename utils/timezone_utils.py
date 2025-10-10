# utils/timezone_utils.py
from datetime import datetime, timedelta
from typing import Optional

def convert_utc_to_user_timezone(
    utc_datetime: datetime, 
    timezone_offset_minutes: Optional[int] = None
) -> datetime:
    """
    Convert UTC datetime to user's timezone.
    
    Args:
        utc_datetime: DateTime in UTC (naive or aware)
        timezone_offset_minutes: Offset from UTC in minutes (from Date.getTimezoneOffset())
                                 Negative for ahead of UTC (e.g., -120 for UTC+2)
                                 Positive for behind UTC (e.g., 300 for UTC-5)
    
    Returns:
        DateTime in user's timezone (naive)
    
    Example:
        UTC: 12:00, offset: -120 (UTC+2) -> Result: 14:00
    """
    if timezone_offset_minutes is None:
        return utc_datetime
    
    # Ensure datetime is naive (no timezone info)
    if utc_datetime.tzinfo is not None:
        utc_datetime = utc_datetime.replace(tzinfo=None)
    
    # JavaScript's getTimezoneOffset() returns negative for ahead of UTC
    # To convert UTC to user time, subtract the offset
    # Example: UTC 12:00 with offset -120 -> 12:00 - (-120 min) = 14:00
    user_datetime = utc_datetime - timedelta(minutes=timezone_offset_minutes)
    
    return user_datetime


def convert_user_to_utc_timezone(
    user_datetime: datetime,
    timezone_offset_minutes: Optional[int] = None
) -> datetime:
    """
    Convert user's local datetime to UTC.
    
    Args:
        user_datetime: DateTime in user's timezone (naive)
        timezone_offset_minutes: Offset from UTC in minutes (from Date.getTimezoneOffset())
                                 Negative for ahead of UTC (e.g., -120 for UTC+2)
                                 Positive for behind UTC (e.g., 300 for UTC-5)
    
    Returns:
        DateTime in UTC (naive)
    
    Example:
        User time: 14:00, offset: -120 (UTC+2) -> Result: 12:00 UTC
    """
    if timezone_offset_minutes is None:
        return user_datetime
    
    # Ensure datetime is naive
    if user_datetime.tzinfo is not None:
        user_datetime = user_datetime.replace(tzinfo=None)
    
    # JavaScript's getTimezoneOffset() returns negative for ahead of UTC
    # To convert user time to UTC, add the offset
    # Example: User 14:00 with offset -120 -> 14:00 + (-120 min) = 12:00 UTC
    utc_datetime = user_datetime + timedelta(minutes=timezone_offset_minutes)
    
    return utc_datetime