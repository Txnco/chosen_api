from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from database import get_db
from auth.jwt import get_current_user
from models.user import User
from schema.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    get_default_notification_preferences
)

notification_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notification_router.get("/preferences", response_model=Dict[str, Any])
def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's notification preferences.
    Returns default preferences if none are set.
    """
    user = db.query(User).filter(
        User.id == current_user["user_id"],
        User.deleted_at == None
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # If user has no preferences set, return defaults
    if user.notification_preferences is None:
        preferences = get_default_notification_preferences()
    else:
        preferences = user.notification_preferences

    return {
        "user_id": user.id,
        "notifications": preferences
    }


@notification_router.put("/preferences", response_model=Dict[str, Any])
def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's notification preferences.
    Only updates the fields that are provided in the request.
    """
    user = db.query(User).filter(
        User.id == current_user["user_id"],
        User.deleted_at == None
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get current preferences or defaults
    if user.notification_preferences is None:
        current_preferences = get_default_notification_preferences()
    else:
        current_preferences = user.notification_preferences

    # Update only the provided fields
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)

    for notification_type, new_values in update_data.items():
        if new_values is not None:
            # Convert Pydantic model to dict if needed
            if hasattr(new_values, 'model_dump'):
                new_values_dict = new_values.model_dump(exclude_none=True)
            else:
                new_values_dict = new_values

            # Update the specific notification type
            if notification_type in current_preferences:
                # Merge with existing values (update only provided fields)
                current_preferences[notification_type].update(new_values_dict)
            else:
                # Add new notification type
                current_preferences[notification_type] = new_values_dict

    # Save updated preferences
    user.notification_preferences = current_preferences

    try:
        db.commit()
        db.refresh(user)

        return {
            "user_id": user.id,
            "notifications": user.notification_preferences
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}"
        )


@notification_router.post("/reset", response_model=Dict[str, Any])
def reset_notification_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset user's notification preferences to default values.
    """
    user = db.query(User).filter(
        User.id == current_user["user_id"],
        User.deleted_at == None
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Reset to default preferences
    user.notification_preferences = get_default_notification_preferences()

    try:
        db.commit()
        db.refresh(user)

        return {
            "user_id": user.id,
            "notifications": user.notification_preferences,
            "message": "Notification preferences reset to defaults"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset notification preferences: {str(e)}"
        )
