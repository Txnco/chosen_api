from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.jwt import get_current_user
from database import get_db
from models.user import User
from models.questionnaire import UserQuestionnaire
from schema.notification import NotificationPreferencesResponse, NotificationPreferencesUpdate, get_default_notification_preferences

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notification_router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    else:
        preferences = user.notification_preferences
    
    # Inject birthday date
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
    
    # Get current preferences or defaults
    current_prefs = user.notification_preferences or get_default_notification_preferences()
    
    # Update with new data
    update_data = data.model_dump(exclude_unset=True)
    
    # Convert integer day values to strings
    VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for notif_type, settings in update_data.items():
        if isinstance(settings, dict) and "day" in settings:
            if isinstance(settings["day"], int):
                settings["day"] = VALID_DAYS[settings["day"] - 1] if 1 <= settings["day"] <= 7 else "monday"
    
    # Merge updates
    for key, value in update_data.items():
        if key in current_prefs:
            current_prefs[key].update(value)
        else:
            current_prefs[key] = value
    
    user.notification_preferences = current_prefs
    db.commit()
    
    # Get birthday for response
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    birthday_date = questionnaire.birthday.isoformat() if questionnaire and questionnaire.birthday else None
    if "birthday" in current_prefs:
        current_prefs["birthday"]["birthday_date"] = birthday_date
    
    return {
        "user_id": user.id,
        "notifications": current_prefs
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
    db.commit()
    
    return {"message": "Notification preferences reset to defaults"}