from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal

from database import get_db
from auth.jwt import get_current_user
from models.user import User
from models.weight_tracking import WeightTracking
from schema.weight_tracking import WeightTrackingCreate, WeightTrackingUpdate, WeightTrackingResponse
from models.day_rating import DayRating
from schema.day_rating import DayRatingCreate, DayRatingUpdate, DayRatingResponse
from models.progress_photos import ProgressPhoto, PhotoAngleEnum
from schema.progress_photos import ProgressPhotoCreate, ProgressPhotoUpdate, ProgressPhotoResponse

from models.user import User

tracking_router = APIRouter(prefix="/tracking", tags=["Tracking"])


@tracking_router.get('/weight', response_model=List[WeightTrackingResponse])
def get_weight(
    user_id: Optional[int] = Query(None, description="User ID (admin only)"),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin accessing another user's data
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can access other users' data"
            )
        target_user_id = user_id
    else:
        # User accessing their own data
        target_user_id = current_user['user_id']
    
    # Get weight tracking entries
    weight_entries = db.query(WeightTracking).filter(
        WeightTracking.user_id == target_user_id,
        WeightTracking.deleted_at == None
    ).order_by(WeightTracking.created_at.desc()).all()
    
    return weight_entries

@tracking_router.post('/weight', response_model=WeightTrackingResponse)
def save_weight(
    weight: Decimal,
    user_id: Optional[int] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin creating entry for another user
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create entries for other users"
            )
        target_user_id = user_id
    else:
        # User creating their own entry
        target_user_id = current_user['user_id']
    
    # Verify target user exists
    target_user = db.query(User).filter(
        User.id == target_user_id,
        User.deleted_at == None
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create weight tracking entry
    new_weight_entry = WeightTracking(
        user_id=target_user_id,
        weight=weight
    )
    
    db.add(new_weight_entry)
    db.commit()
    db.refresh(new_weight_entry)
    
    return new_weight_entry

@tracking_router.put('/weight/{weight_id}', response_model=WeightTrackingResponse)
def update_weight(
    weight_id: int,
    weight: Decimal,
    user_id: Optional[int] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Find the weight entry
    weight_entry = db.query(WeightTracking).filter(
        WeightTracking.id == weight_id,
        WeightTracking.deleted_at == None
    ).first()
    
    if not weight_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weight entry not found"
        )
    
    # Check permissions
    if current_user['role_id'] == 1:
        # Admin can update any entry
        pass
    else:
        # Regular user can only update their own entries
        if weight_entry.user_id != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own weight entries"
            )
    
    # Update the weight
    weight_entry.weight = weight
    
    db.commit()
    db.refresh(weight_entry)
    
    return weight_entry

@tracking_router.get('/day-rating', response_model=List[DayRatingResponse])
def get_day_rating(
    user_id: Optional[int] = Query(None, description="User ID (admin only)"),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin accessing another user's data
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can access other users' data"
            )
        target_user_id = user_id
    else:
        # User accessing their own data
        target_user_id = current_user['user_id']
    
    # Get day rating entries
    day_ratings = db.query(DayRating).filter(
        DayRating.user_id == target_user_id
    ).order_by(DayRating.created_at.desc()).all()
    
    return day_ratings

@tracking_router.post('/day-rating', response_model=DayRatingResponse)
def create_day_rating(
    score: Optional[int] = None,
    note: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin creating entry for another user
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create entries for other users"
            )
        target_user_id = user_id
    else:
        # User creating their own entry
        target_user_id = current_user['user_id']
    
    # Verify target user exists
    target_user = db.query(User).filter(
        User.id == target_user_id,
        User.deleted_at == None
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate score range
    if score is not None and (score < 0 or score > 255):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score must be between 0 and 255"
        )
    
    # Create day rating entry
    new_day_rating = DayRating(
        user_id=target_user_id,
        score=score,
        note=note
    )
    
    db.add(new_day_rating)
    db.commit()
    db.refresh(new_day_rating)
    
    return new_day_rating

@tracking_router.put('/day-rating/{rating_id}', response_model=DayRatingResponse)
def update_day_rating(
    rating_id: int,
    score: Optional[int] = None,
    note: Optional[str] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Find the day rating entry
    day_rating = db.query(DayRating).filter(
        DayRating.id == rating_id
    ).first()
    
    if not day_rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Day rating not found"
        )
    
    # Check permissions
    if current_user['role_id'] == 1:
        # Admin can update any entry
        pass
    else:
        # Regular user can only update their own entries
        if day_rating.user_id != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own day ratings"
            )
    
    # Validate score range if provided
    if score is not None and (score < 0 or score > 255):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score must be between 0 and 255"
        )
    
    # Update the fields if provided
    if score is not None:
        day_rating.score = score
    if note is not None:
        day_rating.note = note
    
    db.commit()
    db.refresh(day_rating)
    
    return day_rating

@tracking_router.get('/progress-photos', response_model=List[ProgressPhotoResponse])
def get_progress_photos(
    user_id: Optional[int] = Query(None, description="User ID (admin only)"),
    angle: Optional[str] = Query(None, description="Filter by photo angle (front, side, back)"),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin accessing another user's data
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can access other users' data"
            )
        target_user_id = user_id
    else:
        # User accessing their own data
        target_user_id = current_user['user_id']
    
    # Build query
    query = db.query(ProgressPhoto).filter(
        ProgressPhoto.user_id == target_user_id,
        ProgressPhoto.deleted_at == None
    )
    
    # Filter by angle if provided
    if angle:
        try:
            angle_enum = PhotoAngleEnum(angle)
            query = query.filter(ProgressPhoto.angle == angle_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid angle. Must be 'front', 'side', or 'back'"
            )
    
    # Get progress photos ordered by most recent
    progress_photos = query.order_by(ProgressPhoto.created_at.desc()).all()
    
    return progress_photos

@tracking_router.post('/progress-photos', response_model=ProgressPhotoResponse)
def save_progress_photos(
    angle: str,
    image_url: str,
    user_id: Optional[int] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Determine target user ID
    if user_id is not None:
        # Admin creating entry for another user
        if current_user['role_id'] != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create entries for other users"
            )
        target_user_id = user_id
    else:
        # User creating their own entry
        target_user_id = current_user['user_id']
    
    # Verify target user exists
    target_user = db.query(User).filter(
        User.id == target_user_id,
        User.deleted_at == None
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate angle enum
    try:
        angle_enum = PhotoAngleEnum(angle)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid angle. Must be 'front', 'side', or 'back'"
        )
    
    # Validate image_url length
    if len(image_url) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image URL too long (max 255 characters)"
        )
    
    # Create progress photo entry
    new_progress_photo = ProgressPhoto(
        user_id=target_user_id,
        angle=angle_enum,
        image_url=image_url
    )
    
    db.add(new_progress_photo)
    db.commit()
    db.refresh(new_progress_photo)
    
    return new_progress_photo

@tracking_router.put('/progress-photos/{progress_id}', response_model=ProgressPhotoResponse)
def update_progress_photos(
    progress_id: int,
    angle: Optional[str] = None,
    image_url: Optional[str] = None,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Find the progress photo entry
    progress_photo = db.query(ProgressPhoto).filter(
        ProgressPhoto.id == progress_id,
        ProgressPhoto.deleted_at == None
    ).first()
    
    if not progress_photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress photo not found"
        )
    
    # Check permissions
    if current_user['role_id'] == 1:
        # Admin can update any entry
        pass
    else:
        # Regular user can only update their own entries
        if progress_photo.user_id != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own progress photos"
            )
    
    # Validate and update angle if provided
    if angle is not None:
        try:
            angle_enum = PhotoAngleEnum(angle)
            progress_photo.angle = angle_enum
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid angle. Must be 'front', 'side', or 'back'"
            )
    
    # Validate and update image_url if provided
    if image_url is not None:
        if len(image_url) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image URL too long (max 255 characters)"
            )
        progress_photo.image_url = image_url
    
    db.commit()
    db.refresh(progress_photo)
    
    return progress_photo