from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from datetime import date
from database import get_db
from auth.jwt import get_current_user
from models.user import User
from sqlalchemy import func
from models.weight_tracking import WeightTracking
from schema.weight_tracking import WeightTrackingCreate, WeightTrackingUpdate, WeightTrackingResponse
from models.day_rating import DayRating
from schema.day_rating import DayRatingCreate, DayRatingUpdate, DayRatingResponse
from models.progress_photos import ProgressPhoto, PhotoAngleEnum
from schema.progress_photos import ProgressPhotoCreate, ProgressPhotoUpdate, ProgressPhotoResponse
from functions.upload import upload_progress

tracking_router = APIRouter(prefix="/tracking", tags=["Tracking"])

# Weight Tracking Endpoints
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
    ).order_by(
        WeightTracking.date.is_(None),            # Push NULL dates to the end
        WeightTracking.date.desc(),               # Sort by date descending
        WeightTracking.created_at.desc()          # Then by created_at
    ).all()
    return weight_entries

@tracking_router.post('/weight', response_model=WeightTrackingResponse)
def save_weight(
    data: WeightTrackingCreate,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
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
        weight=data.weight,
        date=data.date
    )
    
    db.add(new_weight_entry)
    db.commit()
    db.refresh(new_weight_entry)
    
    return new_weight_entry

@tracking_router.put('/weight/{weight_id}', response_model=WeightTrackingResponse)
def update_weight(
    weight_id: int,
    data: WeightTrackingUpdate,
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
    weight_entry.weight = data.weight
    
    db.commit()
    db.refresh(weight_entry)
    
    return weight_entry

# Day Rating Endpoints
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
    data: DayRatingCreate,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
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
    
    today = date.today()
    existing_rating = db.query(DayRating).filter(
        DayRating.user_id == target_user_id,
        func.date(DayRating.created_at) == today
    ).first()

    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already rated today. You can edit your existing rating instead."
        )
        
    # Validate score range
    if data.score is not None and (data.score < 0 or data.score > 255):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score must be between 0 and 255"
        )
    
    # Create day rating entry
    new_day_rating = DayRating(
        user_id=target_user_id,
        score=data.score,
        note=data.note
    )
    
    db.add(new_day_rating)
    db.commit()
    db.refresh(new_day_rating)
    
    return new_day_rating

@tracking_router.put('/day-rating/{rating_id}', response_model=DayRatingResponse)
def update_day_rating(
    rating_id: int,
    data: DayRatingUpdate,
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
    if data.score is not None and (data.score < 0 or data.score > 255):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score must be between 0 and 255"
        )
    
    # Update the fields if provided
    if data.score is not None:
        day_rating.score = data.score
    if data.note is not None:
        day_rating.note = data.note
    
    db.commit()
    db.refresh(day_rating)
    
    return day_rating

# Progress Photos Endpoints
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
def save_progress_photos_with_upload(
    angle: str = Form(..., description="Photo angle (front, side, back)"),
    file: UploadFile = File(..., description="Progress photo image"),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
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
    
    # Upload the image
    try:
        filename = upload_progress(file)
        image_url = f"{filename}"
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
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

@tracking_router.post('/progress-photos/url', response_model=ProgressPhotoResponse)
def save_progress_photos_with_url(
    data: ProgressPhotoCreate,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Alternative endpoint for saving progress photos with URL (for testing)"""
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
        angle_enum = PhotoAngleEnum(data.angle)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid angle. Must be 'front', 'side', or 'back'"
        )
    
    # Validate image_url length
    if len(data.image_url) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image URL too long (max 255 characters)"
        )
    
    # Create progress photo entry
    new_progress_photo = ProgressPhoto(
        user_id=target_user_id,
        angle=angle_enum,
        image_url=data.image_url
    )
    
    db.add(new_progress_photo)
    db.commit()
    db.refresh(new_progress_photo)
    
    return new_progress_photo

@tracking_router.put('/progress-photos/{progress_id}', response_model=ProgressPhotoResponse)
def update_progress_photos(
    progress_id: int,
    data: ProgressPhotoUpdate,
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
    if data.angle is not None:
        try:
            angle_enum = PhotoAngleEnum(data.angle)
            progress_photo.angle = angle_enum
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid angle. Must be 'front', 'side', or 'back'"
            )
    
    # Validate and update image_url if provided
    if data.image_url is not None:
        if len(data.image_url) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image URL too long (max 255 characters)"
            )
        progress_photo.image_url = data.image_url
    
    db.commit()
    db.refresh(progress_photo)
    
    return progress_photo