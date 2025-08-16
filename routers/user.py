from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal

from database import get_db
from auth.jwt import get_current_user
from models.user import User
from models.weight_tracking import WeightTracking
from schema.weight_tracking import WeightTrackingCreate, WeightTrackingUpdate, WeightTrackingResponse

from models.user import User

user_router = APIRouter(prefix="/user", tags=["User"])

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
