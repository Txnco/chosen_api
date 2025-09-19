from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc
from typing import Optional, List
from datetime import datetime, date, timedelta
from database import get_db
from auth.jwt import get_current_user
from models.water import WaterGoal, WaterTracking
from schema.water import (
    WaterGoalCreate, WaterGoalUpdate, WaterGoalResponse,
    WaterTrackingCreate, WaterTrackingUpdate, WaterTrackingResponse
)

water_router = APIRouter(prefix="/water", tags=["Water Tracking"])

# =================== WATER GOALS ===================

@water_router.post("/goal", response_model=WaterGoalResponse)
def create_water_goal(
    data: WaterGoalCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update user's daily water goal"""
    # Check if user already has a goal
    existing_goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    
    if existing_goal:
        # Update existing goal
        existing_goal.daily_ml = data.daily_ml
        existing_goal.updated_at = func.current_timestamp()
        
        try:
            db.commit()
            db.refresh(existing_goal)
            return existing_goal
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update water goal: {str(e)}"
            )
    else:
        # Create new goal
        water_goal = WaterGoal(
            user_id=current_user["user_id"],
            daily_ml=data.daily_ml
        )
        
        try:
            db.add(water_goal)
            db.commit()
            db.refresh(water_goal)
            return water_goal
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create water goal: {str(e)}"
            )

@water_router.get("/goal", response_model=Optional[WaterGoalResponse])
def get_user_water_goal(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's water goal"""
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    
    return goal

@water_router.put("/goal", response_model=WaterGoalResponse)
def update_water_goal(
    data: WaterGoalUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's water goal"""
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water goal not found"
        )
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    goal.updated_at = func.current_timestamp()
    
    try:
        db.commit()
        db.refresh(goal)
        return goal
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update water goal: {str(e)}"
        )

@water_router.delete("/goal")
def delete_water_goal(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user's water goal"""
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water goal not found"
        )
    
    try:
        db.delete(goal)
        db.commit()
        return {"message": "Water goal deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete water goal: {str(e)}"
        )

# =================== WATER TRACKING ===================

@water_router.post("/intake", response_model=WaterTrackingResponse)
def add_water_intake(
    data: WaterTrackingCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add water intake entry"""
    water_entry = WaterTracking(
        user_id=current_user["user_id"],
        water_intake=data.water_intake
    )
    
    try:
        db.add(water_entry)
        db.commit()
        db.refresh(water_entry)
        return water_entry
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add water intake: {str(e)}"
        )

@water_router.get("/intake", response_model=List[WaterTrackingResponse])
def get_water_intake_entries(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get water intake entries with optional date filtering"""
    query = db.query(WaterTracking).filter(
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None)
    )
    
    # Date filtering
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(WaterTracking.created_at >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(WaterTracking.created_at <= end_datetime)
    
    # Sorting
    if order == "desc":
        query = query.order_by(desc(WaterTracking.created_at))
    else:
        query = query.order_by(asc(WaterTracking.created_at))
    
    # Pagination
    entries = query.offset(offset).limit(limit).all()
    
    return entries

@water_router.get("/intake/{entry_id}", response_model=WaterTrackingResponse)
def get_water_intake_entry(
    entry_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific water intake entry by ID"""
    entry = db.query(WaterTracking).filter(
        WaterTracking.id == entry_id,
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None)
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water intake entry not found"
        )
    
    return entry

@water_router.put("/intake/{entry_id}", response_model=WaterTrackingResponse)
def update_water_intake_entry(
    entry_id: int,
    data: WaterTrackingUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update water intake entry"""
    entry = db.query(WaterTracking).filter(
        WaterTracking.id == entry_id,
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None)
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water intake entry not found"
        )
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    entry.updated_at = func.current_timestamp()
    
    try:
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update water intake entry: {str(e)}"
        )

@water_router.delete("/intake/{entry_id}")
def delete_water_intake_entry(
    entry_id: int,
    hard_delete: bool = Query(False, description="Permanently delete entry"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete water intake entry (soft delete by default)"""
    entry = db.query(WaterTracking).filter(
        WaterTracking.id == entry_id,
        WaterTracking.user_id == current_user["user_id"]
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water intake entry not found"
        )
    
    # Check if already soft deleted
    if not hard_delete and entry.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entry already deleted"
        )
    
    try:
        if hard_delete:
            # Permanently delete
            db.delete(entry)
        else:
            # Soft delete
            entry.deleted_at = func.current_timestamp()
            entry.updated_at = func.current_timestamp()
        
        db.commit()
        
        action = "permanently deleted" if hard_delete else "deleted"
        return {"message": f"Water intake entry {action} successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete water intake entry: {str(e)}"
        )

# =================== STATISTICS & ANALYTICS ===================

@water_router.get("/stats/daily")
def get_daily_water_stats(
    target_date: Optional[date] = Query(None, description="Target date (YYYY-MM-DD), defaults to today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily water intake statistics"""
    if not target_date:
        target_date = date.today()
    
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Get daily intake total
    daily_total = db.query(
        func.coalesce(func.sum(WaterTracking.water_intake), 0).label('total_intake'),
        func.count(WaterTracking.id).label('entry_count')
    ).filter(
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None),
        WaterTracking.created_at >= start_datetime,
        WaterTracking.created_at <= end_datetime
    ).first()
    
    # Get user's goal
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    
    goal_ml = goal.daily_ml if goal else 2000  # Default 2L if no goal set
    total_intake = daily_total.total_intake if daily_total else 0
    entry_count = daily_total.entry_count if daily_total else 0
    
    progress_percentage = (total_intake / goal_ml * 100) if goal_ml > 0 else 0
    
    return {
        "date": target_date,
        "total_intake_ml": total_intake,
        "goal_ml": goal_ml,
        "progress_percentage": min(progress_percentage, 100),  # Cap at 100%
        "goal_reached": total_intake >= goal_ml,
        "entry_count": entry_count,
        "remaining_ml": max(0, goal_ml - total_intake)
    }

@water_router.get("/stats/weekly")
def get_weekly_water_stats(
    week_start: Optional[date] = Query(None, description="Week start date (YYYY-MM-DD), defaults to current week"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get weekly water intake statistics"""
    if not week_start:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday of current week
    
    week_end = week_start + timedelta(days=6)  # Sunday
    
    start_datetime = datetime.combine(week_start, datetime.min.time())
    end_datetime = datetime.combine(week_end, datetime.max.time())
    
    # Get daily totals for the week
    daily_stats = db.query(
        func.date(WaterTracking.created_at).label('day'),
        func.coalesce(func.sum(WaterTracking.water_intake), 0).label('daily_total'),
        func.count(WaterTracking.id).label('entry_count')
    ).filter(
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None),
        WaterTracking.created_at >= start_datetime,
        WaterTracking.created_at <= end_datetime
    ).group_by(func.date(WaterTracking.created_at)).all()
    
    # Get user's goal
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    goal_ml = goal.daily_ml if goal else 2000
    
    # Calculate weekly totals
    week_total = sum(day.daily_total for day in daily_stats)
    week_goal = goal_ml * 7
    days_with_goal_reached = sum(1 for day in daily_stats if day.daily_total >= goal_ml)
    
    # Build daily breakdown
    daily_breakdown = []
    current_date = week_start
    for i in range(7):
        day_data = next((day for day in daily_stats if day.day == current_date), None)
        daily_breakdown.append({
            "date": current_date,
            "intake_ml": day_data.daily_total if day_data else 0,
            "entry_count": day_data.entry_count if day_data else 0,
            "goal_reached": (day_data.daily_total if day_data else 0) >= goal_ml
        })
        current_date += timedelta(days=1)
    
    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_intake_ml": week_total,
        "week_goal_ml": week_goal,
        "daily_goal_ml": goal_ml,
        "progress_percentage": min((week_total / week_goal * 100) if week_goal > 0 else 0, 100),
        "days_goal_reached": days_with_goal_reached,
        "daily_breakdown": daily_breakdown
    }

@water_router.get("/stats/monthly")
def get_monthly_water_stats(
    year: int = Query(None, description="Year (defaults to current year)"),
    month: int = Query(None, description="Month 1-12 (defaults to current month)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly water intake statistics"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    # Validate month
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12"
        )
    
    # Get first and last day of month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    start_datetime = datetime.combine(first_day, datetime.min.time())
    end_datetime = datetime.combine(last_day, datetime.max.time())
    
    # Get daily totals for the month
    daily_stats = db.query(
        func.date(WaterTracking.created_at).label('day'),
        func.coalesce(func.sum(WaterTracking.water_intake), 0).label('daily_total'),
        func.count(WaterTracking.id).label('entry_count')
    ).filter(
        WaterTracking.user_id == current_user["user_id"],
        WaterTracking.deleted_at.is_(None),
        WaterTracking.created_at >= start_datetime,
        WaterTracking.created_at <= end_datetime
    ).group_by(func.date(WaterTracking.created_at)).all()
    
    # Get user's goal
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == current_user["user_id"]
    ).first()
    goal_ml = goal.daily_ml if goal else 2000
    
    # Calculate monthly totals
    month_total = sum(day.daily_total for day in daily_stats)
    days_in_month = (last_day - first_day).days + 1
    month_goal = goal_ml * days_in_month
    days_with_goal_reached = sum(1 for day in daily_stats if day.daily_total >= goal_ml)
    average_daily = month_total / days_in_month if days_in_month > 0 else 0
    
    return {
        "year": year,
        "month": month,
        "first_day": first_day,
        "last_day": last_day,
        "total_intake_ml": month_total,
        "month_goal_ml": month_goal,
        "daily_goal_ml": goal_ml,
        "progress_percentage": min((month_total / month_goal * 100) if month_goal > 0 else 0, 100),
        "days_goal_reached": days_with_goal_reached,
        "days_in_month": days_in_month,
        "average_daily_ml": round(average_daily, 2),
        "total_entries": sum(day.entry_count for day in daily_stats)
    }

# =================== ADMIN ROUTES ===================

@water_router.get("/admin/user/{user_id}/stats/daily")
def get_user_daily_water_stats(
    user_id: int,
    target_date: Optional[date] = Query(None, description="Target date (YYYY-MM-DD), defaults to today"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin: Get daily water stats for specific user"""
    # Check admin privileges
    if current_user['role_id'] != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    if not target_date:
        target_date = date.today()
    
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Get daily intake total for specified user
    daily_total = db.query(
        func.coalesce(func.sum(WaterTracking.water_intake), 0).label('total_intake'),
        func.count(WaterTracking.id).label('entry_count')
    ).filter(
        WaterTracking.user_id == user_id,
        WaterTracking.deleted_at.is_(None),
        WaterTracking.created_at >= start_datetime,
        WaterTracking.created_at <= end_datetime
    ).first()
    
    # Get user's goal
    goal = db.query(WaterGoal).filter(
        WaterGoal.user_id == user_id
    ).first()
    
    goal_ml = goal.daily_ml if goal else 2000
    total_intake = daily_total.total_intake if daily_total else 0
    entry_count = daily_total.entry_count if daily_total else 0
    
    progress_percentage = (total_intake / goal_ml * 100) if goal_ml > 0 else 0
    
    return {
        "user_id": user_id,
        "date": target_date,
        "total_intake_ml": total_intake,
        "goal_ml": goal_ml,
        "progress_percentage": min(progress_percentage, 100),
        "goal_reached": total_intake >= goal_ml,
        "entry_count": entry_count,
        "remaining_ml": max(0, goal_ml - total_intake)
    }