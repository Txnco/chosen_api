from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
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

@notification_router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notification preferences"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get birthday from questionnaire
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    birthday_date = questionnaire.birthday.isoformat() if questionnaire and questionnaire.birthday else None
    
    # Get preferences or use defaults
    if not user.notification_preferences:
        preferences = get_default_notification_preferences()
        user.notification_preferences = preferences
        db.commit()
        db.refresh(user)
    else:
        preferences = user.notification_preferences.copy()
    
    # Inject birthday date into response
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
    """Update user's notification preferences"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get current preferences or defaults
    current_prefs = user.notification_preferences.copy() if user.notification_preferences else get_default_notification_preferences()
    
    # Convert incoming data to dict, excluding unset values
    update_data = data.model_dump(exclude_unset=True)
    
    # Convert integer day values to strings if present
    VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for notif_type, settings in update_data.items():
        if isinstance(settings, dict) and "day" in settings:
            if isinstance(settings["day"], int):
                day_index = settings["day"] - 1
                settings["day"] = VALID_DAYS[day_index] if 0 <= day_index < 7 else "monday"
    
    # Merge updates into current preferences
    for key, value in update_data.items():
        if key in current_prefs and isinstance(value, dict):
            # Update only the provided fields, preserve others
            current_prefs[key].update(value)
        else:
            current_prefs[key] = value
    
    # Save to database
    user.notification_preferences = current_prefs
    db.commit()
    db.refresh(user)
    
    # Get birthday for response
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    birthday_date = questionnaire.birthday.isoformat() if questionnaire and questionnaire.birthday else None
    
    # Add birthday date to response
    response_prefs = current_prefs.copy()
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
    """Reset notification preferences to defaults"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Reset to defaults
    user.notification_preferences = get_default_notification_preferences()
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Notification preferences reset to defaults",
        "notifications": user.notification_preferences
    }