from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel
from pydantic import BaseModel, EmailStr
from typing import Optional
from passlib.context import CryptContext

from database import get_db
from auth.jwt import get_current_user, require_admin
from models.user import User
from models.weight_tracking import WeightTracking
from schema.weight_tracking import WeightTrackingCreate, WeightTrackingUpdate, WeightTrackingResponse
from functions.upload import upload_profile_image
from functions.send_mail import send_password_reset_email, generate_reset_token, get_reset_token_expiry
from models.user import User


import logging
logger = logging.getLogger("chosen_api")

user_router = APIRouter(prefix="/user", tags=["User"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@user_router.get('/me')
def get_current_user(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id'], User.deleted_at == None).first()
    
    # Check questionnaire status
    from models.questionnaire import UserQuestionnaire
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == user.id
    ).first()
    
    needs_questionnaire_update = False
    if questionnaire:
        # Check if any required fields are null
        needs_questionnaire_update = (
            questionnaire.weight is None or
            questionnaire.height is None or
            questionnaire.birthday is None or
            questionnaire.workout_environment is None or
            questionnaire.work_shifts is None or
            len(questionnaire.work_shifts or []) == 0 or
            questionnaire.wake_up_time is None or
            questionnaire.sleep_time is None or
            questionnaire.morning_routine is None or
            questionnaire.evening_routine is None
        )
    else:
        # No questionnaire at all
        needs_questionnaire_update = True
    birthdate = questionnaire.birthday if questionnaire else None
    return {
        "user_id": user.id,
        "role_id": user.role_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "profile_picture": user.profile_picture,
        "needs_questionnaire_update": needs_questionnaire_update,
        "birthdate" : birthdate,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

@user_router.get('/{user_id}')
def get_user_by_id(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user information by ID"""
    if current_user['role_id'] != 1 and current_user['user_id'] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at == None
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check questionnaire status
    from models.questionnaire import UserQuestionnaire
    questionnaire = db.query(UserQuestionnaire).filter(
        UserQuestionnaire.user_id == user.id
    ).first()
    
    needs_questionnaire_update = False
    if questionnaire:
        needs_questionnaire_update = (
            questionnaire.weight is None or
            questionnaire.height is None or
            questionnaire.birthday is None or
            questionnaire.workout_environment is None or
            questionnaire.work_shifts is None or
            len(questionnaire.work_shifts or []) == 0 or
            questionnaire.wake_up_time is None or
            questionnaire.sleep_time is None or
            questionnaire.morning_routine is None or
            questionnaire.evening_routine is None
        )
    else:
        needs_questionnaire_update = True
    birthdate = questionnaire.birthday if questionnaire else None
    return {
        "user_id": user.id,
        "role_id": user.role_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "profile_picture": user.profile_picture,
        "needs_questionnaire_update": needs_questionnaire_update,
        "birthdate" : birthdate,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

@user_router.get('/')
def get_all_users(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.deleted_at == None).all()
    return [
        {
            "user_id": user.id,
            "role_id": user.role_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "profile_picture": user.profile_picture,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        for user in users
    ]

@user_router.delete('/{user_id}')
def delete_user(
    user_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at == None).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.deleted_at = datetime.now()
    db.commit()
    
    return {"message": f"User {user_id} deleted"}

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_id: Optional[int] = None

@user_router.put("/{user_id}")
def update_user(
    user_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role_id: Optional[int] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    # 1. Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    # # 2. Check for duplicate email if updated
    # if email and email != user.email:
    #     existing_user = db.query(User).filter(User.email == email).first()
    #     if existing_user:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="Email already in use",
    #         )

    # 3. Handle profile picture upload
    if profile_picture:
        try:
            filename = upload_profile_image(profile_picture)
            user.profile_picture = filename
        except HTTPException:
            # HTTPExceptions are already meaningful; still log with stack
            logger.exception("HTTP error while uploading profile for user_id=%s", user_id)
            raise
        except Exception as e:
            # Log full traceback and context BEFORE raising
            logger.exception(
                "Unexpected error uploading profile picture for user_id=%s, filename=%s",
                user_id,
                getattr(profile_picture, "filename", None),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload profile picture: {str(e)}"
            )

    # 4. Update only provided fields
    if email:
        user.email = email
    if password:
        user.password_hash = pwd_context.hash(password)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    if role_id is not None:
        user.role_id = role_id

    # 5. Save changes
    db.commit()
    db.refresh(user)

    return {
        "message": f"User {user.id} updated by admin {current_user['user_id']}",
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role_id": user.role_id,
            "profile_picture": user.profile_picture,
        },
    }


class PasswordResetRequest(BaseModel):
    email: EmailStr


@user_router.post('/request-password-reset')
def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email (public endpoint).
    Sends a reset token to the user's email if the account exists.
    """
    user = db.query(User).filter(
        User.email == request.email,
        User.deleted_at == None
    ).first()

    # Always return success to prevent email enumeration
    if not user:
        return {"message": "Ako račun postoji, e-mail za resetiranje lozinke je poslan."}

    # Generate reset token and set expiry
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expires_at = get_reset_token_expiry(hours=24)
    db.commit()

    # Send password reset email
    send_password_reset_email(
        first_name=user.first_name,
        email=user.email,
        reset_token=reset_token
    )

    return {"message": "Ako račun postoji, e-mail za resetiranje lozinke je poslan."}


@user_router.post('/{user_id}/admin-reset-password')
def admin_reset_password(
    user_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to trigger a password reset email for another user.
    Generates a reset token and sends an email to the target user.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at == None
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Korisnik nije pronađen"
        )

    # Generate reset token and set expiry
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expires_at = get_reset_token_expiry(hours=24)
    db.commit()

    # Send password reset email
    send_password_reset_email(
        first_name=user.first_name,
        email=user.email,
        reset_token=reset_token
    )

    return {
        "message": f"E-mail za resetiranje lozinke poslan korisniku {user.email}",
        "user_id": user.id,
        "email": user.email
    }


@user_router.post('/fcm-token')
def save_fcm_token(
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save FCM token for push notifications"""
    user_id = current_user['user_id']
    fcm_token = data.get('fcm_token')
    
    if not fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FCM token is required"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.fcm_token = fcm_token
    db.commit()
    
    logger.info(f"FCM token saved for user {user_id}")
    return {"message": "FCM token saved successfully"}


@user_router.delete('/fcm-token')
def delete_fcm_token(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete FCM token on logout"""
    user_id = current_user['user_id']
    
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.fcm_token = None
        db.commit()
        logger.info(f"FCM token deleted for user {user_id}")
    
    return {"message": "FCM token deleted successfully"}

