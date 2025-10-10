from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth.jwt import get_current_user, require_admin
from models.event import Event, EventCopy, RepeatTypeEnum
from models.user import User
from schema.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventWithUser,
    EventCopyCreate,
    EventCopyResponse,
    EventBulkCopyCreate
)
from utils.timezone_utils import convert_utc_to_user_timezone, convert_user_to_utc_timezone
from typing import Optional, List
from datetime import datetime, timedelta

# For monthly/yearly repeat - install: pip install python-dateutil
try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not installed
    relativedelta = None

event_router = APIRouter(prefix="/events", tags=["Events"])


def apply_timezone_to_event(event_dict: dict, timezone_offset_minutes: Optional[int]) -> dict:
    """Apply timezone conversion to event datetime fields"""
    if timezone_offset_minutes is not None:
        if event_dict.get("start_time"):
            event_dict["start_time"] = convert_utc_to_user_timezone(
                event_dict["start_time"], 
                timezone_offset_minutes
            )
        if event_dict.get("end_time"):
            event_dict["end_time"] = convert_utc_to_user_timezone(
                event_dict["end_time"], 
                timezone_offset_minutes
            )
        if event_dict.get("repeat_until"):
            event_dict["repeat_until"] = convert_utc_to_user_timezone(
                event_dict["repeat_until"], 
                timezone_offset_minutes
            )
    return event_dict


def event_to_dict_with_timezone(event: Event, timezone_offset_minutes: Optional[int]) -> dict:
    """Convert event to dict and apply timezone"""
    event_dict = {
        "id": event.id,
        "user_id": event.user_id,
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "all_day": event.all_day,
        "repeat_type": event.repeat_type,
        "repeat_until": event.repeat_until,
        "created_by": event.created_by,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }
    return apply_timezone_to_event(event_dict, timezone_offset_minutes)


def generate_repeat_instances(
    event: Event, 
    start_date: datetime, 
    end_date: datetime,
    timezone_offset_minutes: Optional[int] = None
) -> List[dict]:
    """Generate repeat instances for an event within a date range"""
    instances = []
    
    if event.repeat_type == RepeatTypeEnum.none:
        return instances
    
    # Start from the NEXT occurrence after the original event
    current_date = event.start_time
    repeat_end = event.repeat_until or end_date
    
    # Move to the first repeat occurrence (skip the original)
    if event.repeat_type == RepeatTypeEnum.daily:
        current_date += timedelta(days=1)
    elif event.repeat_type == RepeatTypeEnum.weekly:
        current_date += timedelta(weeks=1)
    elif event.repeat_type == RepeatTypeEnum.monthly:
        if relativedelta:
            current_date += relativedelta(months=1)
        else:
            # Fallback: approximate month as 30 days
            current_date += timedelta(days=30)
    elif event.repeat_type == RepeatTypeEnum.yearly:
        if relativedelta:
            current_date += relativedelta(years=1)
        else:
            # Fallback: approximate year as 365 days
            current_date += timedelta(days=365)
    
    # Generate instances for each repeat occurrence
    while current_date <= min(repeat_end, end_date):
        # Only include if it's within the requested date range
        duration = event.end_time - event.start_time
        instance_end = current_date + duration
        
        # Check if instance overlaps with requested range
        if instance_end >= start_date:
            instance_dict = {
                "id": event.id,  # Keep same ID so we know which event this is an instance of
                "user_id": event.user_id,
                "title": event.title,
                "description": event.description,
                "start_time": current_date,
                "end_time": instance_end,
                "all_day": event.all_day,
                "repeat_type": event.repeat_type.value,
                "repeat_until": event.repeat_until,
                "created_by": event.created_by,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
                "is_repeat_instance": True,  # Mark as instance
                "original_start": event.start_time  # Keep reference to original
            }
            instances.append(apply_timezone_to_event(instance_dict, timezone_offset_minutes))
        
        # Move to next occurrence
        if event.repeat_type == RepeatTypeEnum.daily:
            current_date += timedelta(days=1)
        elif event.repeat_type == RepeatTypeEnum.weekly:
            current_date += timedelta(weeks=1)
        elif event.repeat_type == RepeatTypeEnum.monthly:
            if relativedelta:
                current_date += relativedelta(months=1)
            else:
                current_date += timedelta(days=30)
        elif event.repeat_type == RepeatTypeEnum.yearly:
            if relativedelta:
                current_date += relativedelta(years=1)
            else:
                current_date += timedelta(days=365)
        else:
            break
    
    return instances


@event_router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    Create a new event.
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC (from JavaScript's Date.getTimezoneOffset())
                          Example: -120 for UTC+2, -60 for UTC+1, 0 for UTC
    """
    
    # Convert times from user timezone to UTC
    start_time_utc = convert_user_to_utc_timezone(data.start_time, timezone_offset)
    end_time_utc = convert_user_to_utc_timezone(data.end_time, timezone_offset)
    
    # Validate that end_time is after start_time
    if end_time_utc <= start_time_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    repeat_until_utc = None
    if data.repeat_until:
        repeat_until_utc = convert_user_to_utc_timezone(data.repeat_until, timezone_offset)
        
        # Validate repeat_until if repeat_type is not none
        if data.repeat_type != RepeatTypeEnum.none:
            if repeat_until_utc <= start_time_utc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Repeat until date must be after start time"
                )
    
    # Check if user exists
    user = db.query(User).filter(User.id == data.user_id, User.deleted_at == None).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only admin can create events for other users
    if current_user["role_id"] != 1 and data.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create events for yourself"
        )
    
    # Create event with UTC times
    event = Event(
        user_id=data.user_id,
        title=data.title,
        description=data.description,
        start_time=start_time_utc,
        end_time=end_time_utc,
        all_day=data.all_day,
        repeat_type=data.repeat_type,
        repeat_until=repeat_until_utc,
        created_by=current_user["user_id"]
    )
    
    try:
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Convert back to user timezone for response
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@event_router.get("/", response_model=List[EventResponse])
def list_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events until this date"),
    include_repeating: bool = Query(True, description="Include repeat instances"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    List events with optional filters.
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC (from JavaScript's Date.getTimezoneOffset())
    """
    
    # Convert filter dates from user timezone to UTC
    start_date_utc = convert_user_to_utc_timezone(start_date, timezone_offset) if start_date else None
    end_date_utc = convert_user_to_utc_timezone(end_date, timezone_offset) if end_date else None
    
    # Build query
    query = db.query(Event)
    
    # Non-admin users can only see their own events
    if current_user["role_id"] != 1:
        query = query.filter(Event.user_id == current_user["user_id"])
    elif user_id:
        query = query.filter(Event.user_id == user_id)
    
    # For repeating events, we need to fetch events that:
    # 1. Start before or during the range
    # 2. Either don't repeat, or repeat_until is after the range start, or repeat_until is null
    if start_date_utc and end_date_utc:
        # Get events that might appear in this range
        query = query.filter(
            Event.start_time <= end_date_utc  # Started before or during range
        ).filter(
            # AND (no repeat OR repeat extends into our range)
            (Event.repeat_type == RepeatTypeEnum.none) |
            (Event.repeat_until.is_(None)) |
            (Event.repeat_until >= start_date_utc)
        )
    elif start_date_utc:
        query = query.filter(Event.start_time >= start_date_utc)
    elif end_date_utc:
        query = query.filter(Event.end_time <= end_date_utc)
    
    events = query.order_by(Event.start_time).all()
    
    # Convert events to user timezone and generate instances
    result_events = []
    
    for event in events:
        # Check if the original event falls within the requested range
        if start_date_utc and end_date_utc:
            # Include original event if it's in range
            if event.start_time >= start_date_utc and event.end_time <= end_date_utc:
                event_dict = event_to_dict_with_timezone(event, timezone_offset)
                result_events.append(EventResponse(**event_dict))
        else:
            # No date filter, include all original events
            event_dict = event_to_dict_with_timezone(event, timezone_offset)
            result_events.append(EventResponse(**event_dict))
        
        # Generate repeat instances if requested
        if include_repeating and start_date_utc and end_date_utc and event.repeat_type != RepeatTypeEnum.none:
            instances = generate_repeat_instances(event, start_date_utc, end_date_utc, timezone_offset)
            result_events.extend([EventResponse(**inst) for inst in instances])
    
    return result_events


@event_router.get("/{event_id}", response_model=EventWithUser)
def get_event(
    event_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    Get details of a specific event.
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC
    """
    
    event = db.query(Event).options(
        joinedload(Event.user),
        joinedload(Event.creator)
    ).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Non-admin users can only view their own events
    if current_user["role_id"] != 1 and event.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own events"
        )
    
    # Convert times to user timezone
    event_dict = event_to_dict_with_timezone(event, timezone_offset)
    
    # Build response with user details
    response = EventWithUser(
        **event_dict,
        user_first_name=event.user.first_name if event.user else None,
        user_last_name=event.user.last_name if event.user else None,
        user_email=event.user.email if event.user else None,
        creator_first_name=event.creator.first_name if event.creator else None,
        creator_last_name=event.creator.last_name if event.creator else None
    )
    
    return response


@event_router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    data: EventUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    Update an existing event (PATCH - partial update).
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC
    """
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Only admin or event creator can update
    if current_user["role_id"] != 1 and event.created_by != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update events you created"
        )
    
    # Get only the fields that were explicitly set
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        # No fields to update, return with timezone conversion
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
    
    # Convert times from user timezone to UTC
    if "start_time" in update_data:
        update_data["start_time"] = convert_user_to_utc_timezone(update_data["start_time"], timezone_offset)
    if "end_time" in update_data:
        update_data["end_time"] = convert_user_to_utc_timezone(update_data["end_time"], timezone_offset)
    if "repeat_until" in update_data and update_data["repeat_until"]:
        update_data["repeat_until"] = convert_user_to_utc_timezone(update_data["repeat_until"], timezone_offset)
    
    # Validate times if either is being updated
    if "start_time" in update_data or "end_time" in update_data:
        start = update_data.get("start_time", event.start_time)
        end = update_data.get("end_time", event.end_time)
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
    
    # Validate repeat_until if updating repeat settings
    if "repeat_until" in update_data and update_data["repeat_until"]:
        start = update_data.get("start_time", event.start_time)
        if update_data["repeat_until"] <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repeat until date must be after start time"
            )
    
    # Apply only the changed fields
    for field, value in update_data.items():
        setattr(event, field, value)
    
    try:
        db.commit()
        db.refresh(event)
        
        # Convert back to user timezone for response
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@event_router.delete("/{event_id}")
def delete_event(
    event_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an event"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Only admin or event creator can delete
    if current_user["role_id"] != 1 and event.created_by != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete events you created"
        )
    
    try:
        db.delete(event)
        db.commit()
        return {"message": "Event deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )


@event_router.post("/{event_id}/copy", response_model=EventCopyResponse, status_code=status.HTTP_201_CREATED)
def copy_event(
    event_id: int,
    data: EventCopyCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    Copy an event to another user/date.
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC
    """
    
    # Only admin can copy events
    if current_user["role_id"] != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can copy events"
        )
    
    # Get original event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if target user exists
    target_user = db.query(User).filter(
        User.id == data.target_user_id,
        User.deleted_at == None
    ).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )
    
    # Convert target date to UTC
    target_date_utc = convert_user_to_utc_timezone(data.target_date, timezone_offset)
    
    # Calculate time difference
    time_diff = target_date_utc - event.start_time
    
    # Create new event (copy)
    new_event = Event(
        user_id=data.target_user_id,
        title=event.title,
        description=event.description,
        start_time=event.start_time + time_diff,
        end_time=event.end_time + time_diff,
        all_day=event.all_day,
        repeat_type=RepeatTypeEnum.none,
        repeat_until=None,
        created_by=current_user["user_id"]
    )
    
    try:
        db.add(new_event)
        db.flush()
        
        # Create event copy record
        event_copy = EventCopy(
            event_id=event_id,
            user_id=data.target_user_id,
            date=target_date_utc
        )
        db.add(event_copy)
        db.commit()
        db.refresh(event_copy)
        
        return event_copy
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to copy event: {str(e)}"
        )


@event_router.post("/{event_id}/bulk-copy", response_model=List[EventCopyResponse], status_code=status.HTTP_201_CREATED)
def bulk_copy_event(
    event_id: int,
    data: EventBulkCopyCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """
    Copy an event to multiple users and/or dates (Admin only).
    
    Headers:
        X-Timezone-Offset: Timezone offset in minutes from UTC
    """
    
    # Get original event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Validate all target users exist
    target_users = db.query(User).filter(
        User.id.in_(data.target_user_ids),
        User.deleted_at == None
    ).all()
    
    if len(target_users) != len(data.target_user_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more target users not found"
        )
    
    copies = []
    
    try:
        for user_id in data.target_user_ids:
            for target_date in data.target_dates:
                # Convert target date to UTC
                target_date_utc = convert_user_to_utc_timezone(target_date, timezone_offset)
                
                # Calculate time difference
                time_diff = target_date_utc - event.start_time
                
                # Create new event (copy)
                new_event = Event(
                    user_id=user_id,
                    title=event.title,
                    description=event.description,
                    start_time=event.start_time + time_diff,
                    end_time=event.end_time + time_diff,
                    all_day=event.all_day,
                    repeat_type=RepeatTypeEnum.none,
                    repeat_until=None,
                    created_by=current_user["user_id"]
                )
                db.add(new_event)
                db.flush()
                
                # Create event copy record
                event_copy = EventCopy(
                    event_id=event_id,
                    user_id=user_id,
                    date=target_date_utc
                )
                db.add(event_copy)
                db.flush()
                copies.append(event_copy)
        
        db.commit()
        
        # Refresh all copies
        for copy in copies:
            db.refresh(copy)
        
        return copies
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk copy event: {str(e)}"
        )


@event_router.get("/{event_id}/copies", response_model=List[EventCopyResponse])
def get_event_copies(
    event_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all copies of an event (Admin only)"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    copies = db.query(EventCopy).filter(EventCopy.event_id == event_id).all()
    return copies