# routers/questionnaire.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import date, time
from decimal import Decimal
from typing import Optional, Dict, Any
from auth.jwt import get_current_user, require_admin
from database import get_db
from models.questionnaire import UserQuestionnaire
from models.weight_tracking import WeightTracking
from models.user import User
from schema.questionnaire import QuestionnaireCreate, QuestionnaireResponse, QuestionnaireUpdate

quest_router = APIRouter(prefix="/questionnaire", tags=["Questionnaire"])


def calculate_notification_preferences(
    wake_up_time: time,
    sleep_time: time,
    user_created_day: int = 1
) -> Dict[str, Any]:
    """
    Calculate notification preferences based on user's wake up and sleep times.

    Water reminders: 30min after wake up, every 2h, last one 1h30min before sleep
    Day rating: 30min before sleep
    Weight tracking: Saturday at wake up time
    Progress photos: Monthly on user creation day
    """
    def time_to_str(t: time) -> str:
        return f"{t.hour:02d}:{t.minute:02d}"

    def add_minutes_to_time(t: time, minutes: int) -> time:
        total_minutes = t.hour * 60 + t.minute + minutes
        # Handle overflow past midnight
        total_minutes = total_minutes % (24 * 60)
        return time(hour=total_minutes // 60, minute=total_minutes % 60)

    def subtract_minutes_from_time(t: time, minutes: int) -> time:
        total_minutes = t.hour * 60 + t.minute - minutes
        # Handle underflow before midnight
        if total_minutes < 0:
            total_minutes += 24 * 60
        return time(hour=total_minutes // 60, minute=total_minutes % 60)

    # Water reminders: start 30min after wake up, end 1h30min before sleep
    water_start = add_minutes_to_time(wake_up_time, 30)
    water_end = subtract_minutes_from_time(sleep_time, 90)

    # Day rating: 30min before sleep
    day_rating_time = subtract_minutes_from_time(sleep_time, 30)

    # Weight tracking: Saturday at wake up time
    weight_time = wake_up_time

    # Progress photo day (clamped to 1-28)
    photo_day = min(max(user_created_day, 1), 28)

    return {
        "daily_planning": {"enabled": True, "time": "20:00"},
        "day_rating": {"enabled": True, "time": time_to_str(day_rating_time)},
        "progress_photo": {"enabled": True, "day_of_month": photo_day, "time": time_to_str(wake_up_time)},
        "weight_tracking": {"enabled": True, "day": "saturday", "time": time_to_str(weight_time)},
        "water_reminders": {
            "enabled": True,
            "interval_hours": 2,
            "start_time": time_to_str(water_start),
            "end_time": time_to_str(water_end)
        },
        "birthday": {"enabled": True, "time": "09:00"},
    }


def update_user_notification_preferences(db: Session, user_id: int, questionnaire_data: dict):
    """
    Update user's notification preferences based on questionnaire data.
    Only updates if wake_up_time and sleep_time are provided.
    """
    wake_up = questionnaire_data.get("wake_up_time")
    sleep = questionnaire_data.get("sleep_time")

    if not wake_up or not sleep:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    # Get user creation day for progress photo
    user_created_day = user.created_at.day if user.created_at else 1

    # Calculate new notification preferences
    new_prefs = calculate_notification_preferences(
        wake_up_time=wake_up,
        sleep_time=sleep,
        user_created_day=user_created_day
    )

    # Update user notification preferences
    user.notification_preferences = new_prefs
    flag_modified(user, "notification_preferences")
    db.commit()


@quest_router.post("/", response_model=QuestionnaireResponse)
def upsert_questionnaire(
    data: QuestionnaireCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["user_id"]
    payload = data.model_dump(exclude_unset=True)
    
    # Convert work_shifts to dict format for JSON storage
    if "work_shifts" in payload and payload["work_shifts"]:
        payload["work_shifts"] = [shift.model_dump() if hasattr(shift, 'model_dump') else shift for shift in payload["work_shifts"]]

    existing = (
        db.query(UserQuestionnaire)
        .filter(UserQuestionnaire.user_id == user_id)
        .first()
    )

    try:
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)

            # Update notification preferences if wake_up_time or sleep_time changed
            if "wake_up_time" in payload or "sleep_time" in payload:
                update_user_notification_preferences(db, user_id, {
                    "wake_up_time": existing.wake_up_time,
                    "sleep_time": existing.sleep_time
                })

            return existing
        else:
            row = UserQuestionnaire(user_id=user_id, **payload)
            db.add(row)
            db.commit()
            db.refresh(row)

            # Log initial weight to weight_tracking as starting point
            if "weight" in payload and payload["weight"] is not None:
                weight_entry = WeightTracking(
                    user_id=user_id,
                    weight=Decimal(str(payload["weight"])),
                    date=date.today()
                )
                db.add(weight_entry)
                db.commit()

            # Set notification preferences based on questionnaire
            if row.wake_up_time and row.sleep_time:
                update_user_notification_preferences(db, user_id, {
                    "wake_up_time": row.wake_up_time,
                    "sleep_time": row.sleep_time
                })

            return row
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upsert failed: {e}")

@quest_router.get("/", response_model=Optional[QuestionnaireResponse])
def get_user_questionnaire(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    return questionnaire

@quest_router.put("/", response_model=QuestionnaireResponse)
def update_questionnaire(
    data: QuestionnaireUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == current_user["user_id"]
    ).first()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found. Use POST to create."
        )

    update_data = data.model_dump(exclude_unset=True)

    # Convert work_shifts to dict format for JSON storage
    if "work_shifts" in update_data and update_data["work_shifts"]:
        update_data["work_shifts"] = [shift.model_dump() if hasattr(shift, 'model_dump') else shift for shift in update_data["work_shifts"]]

    for field, value in update_data.items():
        setattr(existing, field, value)

    try:
        db.commit()
        db.refresh(existing)

        # Update notification preferences if wake_up_time or sleep_time changed
        if "wake_up_time" in update_data or "sleep_time" in update_data:
            update_user_notification_preferences(db, current_user["user_id"], {
                "wake_up_time": existing.wake_up_time,
                "sleep_time": existing.sleep_time
            })

        return existing
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update questionnaire: {str(e)}"
        )

@quest_router.get("/admin/user/{user_id}", response_model=Optional[QuestionnaireResponse])
def get_user_questionnaire_admin(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == user_id
    ).first()
    return questionnaire