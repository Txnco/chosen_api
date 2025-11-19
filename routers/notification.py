from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import time, timedelta
from auth.jwt import get_current_user
from database import get_db
from models.user import User
from models.questionnaire import UserQuestionnaire
from schema.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    get_default_notification_preferences
)

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

def calculate_notification_times(questionnaire: UserQuestionnaire) -> dict:
    """Calculate notification times based on questionnaire data"""
    times = {}
    
    if questionnaire.wake_up_time and questionnaire.sleep_time:
        # Water reminders: start 30min after wake up
        wake_dt = questionnaire.wake_up_time
        water_start = (timedelta(hours=wake_dt.hour, minutes=wake_dt.minute) + timedelta(minutes=30))
        times['water_start'] = f"{int(water_start.total_seconds() // 3600):02d}:{int((water_start.total_seconds() % 3600) // 60):02d}"
        
        # Water reminders: end 90min before sleep
        sleep_dt = questionnaire.sleep_time
        water_end = (timedelta(hours=sleep_dt.hour, minutes=sleep_dt.minute) - timedelta(minutes=90))
        times['water_end'] = f"{int(water_end.total_seconds() // 3600):02d}:{int((water_end.total_seconds() % 3600) // 60):02d}"
        
        # Day rating: 30min before sleep
        day_rating = (timedelta(hours=sleep_dt.hour, minutes=sleep_dt.minute) - timedelta(minutes=30))
        times['day_rating'] = f"{int(day_rating.total_seconds() // 3600):02d}:{int((day_rating.total_seconds() % 3600) // 60):02d}"
        
        # Weight tracking: Saturday at wake up time
        times['weight_tracking'] = f"{wake_dt.hour:02d}:{wake_dt.minute:02d}"
    
    return times

@notification_router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    birthday_date = questionnaire.birthday.isoformat() if questionnaire and questionnaire.birthday else None
    
    if not user.notification_preferences:
        preferences = get_default_notification_preferences()
        user.notification_preferences = preferences
        db.commit()
        db.refresh(user)
    else:
        preferences = user.notification_preferences.copy()
    
    # Inject calculated times from questionnaire
    if questionnaire:
        calculated = calculate_notification_times(questionnaire)
        
        if "water_start" in calculated:
            preferences["water_reminders"]["start_time"] = calculated["water_start"]
            preferences["water_reminders"]["end_time"] = calculated["water_end"]
        
        if "day_rating" in calculated:
            preferences["day_rating"]["calculated_time"] = calculated["day_rating"]
        
        if "weight_tracking" in calculated:
            preferences["weight_tracking"]["calculated_time"] = calculated["weight_tracking"]
            preferences["weight_tracking"]["day"] = "saturday"
    
    if "birthday" in preferences:
        preferences["birthday"]["birthday_date"] = birthday_date
    
    return {
        "user_id": user.id,
        "notifications": preferences
    }

@notification_router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_prefs = user.notification_preferences.copy() if user.notification_preferences else get_default_notification_preferences()
    
    update_data = data.model_dump(exclude_unset=True)
    
    VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for notif_type, settings in update_data.items():
        if isinstance(settings, dict) and "day" in settings:
            if isinstance(settings["day"], int):
                day_index = settings["day"] - 1
                settings["day"] = VALID_DAYS[day_index] if 0 <= day_index < 7 else "monday"
    
    for key, value in update_data.items():
        if key in current_prefs and isinstance(value, dict):
            current_prefs[key].update(value)
        else:
            current_prefs[key] = value
    
    user.notification_preferences = current_prefs
    flag_modified(user, "notification_preferences")
    
    db.commit()
    db.refresh(user)
    
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    birthday_date = questionnaire.birthday.isoformat() if questionnaire and questionnaire.birthday else None
    
    response_prefs = current_prefs.copy()
    
    # Inject calculated times
    if questionnaire:
        calculated = calculate_notification_times(questionnaire)
        
        if "water_start" in calculated:
            response_prefs["water_reminders"]["start_time"] = calculated["water_start"]
            response_prefs["water_reminders"]["end_time"] = calculated["water_end"]
        
        if "day_rating" in calculated:
            response_prefs["day_rating"]["calculated_time"] = calculated["day_rating"]
        
        if "weight_tracking" in calculated:
            response_prefs["weight_tracking"]["calculated_time"] = calculated["weight_tracking"]
    
    if "birthday" in response_prefs:
        response_prefs["birthday"]["birthday_date"] = birthday_date
    
    return {
        "user_id": user.id,
        "notifications": response_prefs
    }

@notification_router.post("/reset")
def reset_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.notification_preferences = get_default_notification_preferences()
    flag_modified(user, "notification_preferences")
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Notification preferences reset to defaults",
        "notifications": user.notification_preferences
    }