from fastapi import APIRouter, Depends, HTTPException, status, Query
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

from models.user import User

user_router = APIRouter(prefix="/user", tags=["User"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@user_router.get('/me')
def get_current_user(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id'], User.deleted_at == None).first()
    return{
        "user_id": user.id,
        "role_id": user.role_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
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
    # Only allow admins to get any user, clients can only get themselves
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
    
    return {
        "user_id": user.id,
        "role_id": user.role_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
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
    data: UserUpdate,
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

    # 2. Check for duplicate email if updated
    if data.email and data.email != user.email:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    # 3. Update only provided fields
    if data.email:
        user.email = data.email
    if data.password:  # optional
        user.password_hash = pwd_context.hash(data.password)
    if data.first_name:
        user.first_name = data.first_name
    if data.last_name:
        user.last_name = data.last_name
    if data.role_id is not None:  # optional
        user.role_id = data.role_id

    # 4. Save changes
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
        },
    }
