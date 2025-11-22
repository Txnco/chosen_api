# routes/event.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth.jwt import get_current_user, require_admin
from models.event import Event, EventCopy, EventException, RepeatTypeEnum, RepeatEndTypeEnum, ExceptionTypeEnum
from models.user import User
from schema.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventWithUser,
    EventCopyCreate,
    EventCopyResponse,
    EventBulkCopyCreate,
    EventEditScope
)
from utils.timezone_utils import convert_utc_to_user_timezone, convert_user_to_utc_timezone
from typing import Optional, List, Dict
from datetime import datetime, timedelta, date

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
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
        # FIXED: Apply timezone to original_start too
        if event_dict.get("original_start"):
            event_dict["original_start"] = convert_utc_to_user_timezone(
                event_dict["original_start"], 
                timezone_offset_minutes
            )
    return event_dict


def event_to_dict_with_timezone(event: Event, timezone_offset_minutes: Optional[int]) -> dict:
    """Convert event to dict and apply timezone"""
    event_dict = {
        "id": event.id,
        "user_id": event.user_id,
        "parent_event_id": event.parent_event_id,
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "all_day": event.all_day,
        "repeat_type": event.repeat_type.value,
        "repeat_interval": event.repeat_interval,
        "repeat_days": event.repeat_days,
        "repeat_until": event.repeat_until,
        "repeat_end_type": event.repeat_end_type.value,
        "repeat_count": event.repeat_count,
        "created_by": event.created_by,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }
    return apply_timezone_to_event(event_dict, timezone_offset_minutes)


def should_include_occurrence(event: Event, occurrence_date: datetime, exceptions: List[EventException]) -> bool:
    """Check if a specific occurrence should be included (not deleted)"""
    occurrence_date_only = occurrence_date.date()
    for exception in exceptions:
        if exception.exception_date == occurrence_date_only and exception.exception_type == ExceptionTypeEnum.deleted:
            return False
    return True


def get_modified_event_for_occurrence(
    event: Event, 
    occurrence_date: datetime, 
    exceptions: List[EventException],
    modified_events_cache: Dict[int, Event]
) -> Optional[Event]:
    """Get the modified event for a specific occurrence, if one exists"""
    occurrence_date_only = occurrence_date.date()
    for exception in exceptions:
        if (exception.exception_date == occurrence_date_only and 
            exception.exception_type == ExceptionTypeEnum.modified and
            exception.modified_event_id):
            # Use cache instead of querying
            return modified_events_cache.get(exception.modified_event_id)
    return None


def calculate_previous_occurrence(event: Event, target_date: datetime) -> datetime:
    """
    Calculate the actual previous occurrence before the target date.
    FIXED: Properly handles different repeat types
    """
    current = event.start_time
    previous = event.start_time
    
    if event.repeat_type == RepeatTypeEnum.daily:
        while current < target_date:
            previous = current
            current += timedelta(days=event.repeat_interval)
    
    elif event.repeat_type == RepeatTypeEnum.weekly:
        if event.repeat_days:
            # For weekly with specific days, find the last occurrence before target
            allowed_weekdays = set(int(d) for d in event.repeat_days.split(','))
            week_number = 0
            
            while True:
                week_start = event.start_time + timedelta(days=week_number * 7)
                if week_start >= target_date:
                    break
                    
                if week_number % event.repeat_interval == 0:
                    for day_offset in range(7):
                        check_date = week_start + timedelta(days=day_offset)
                        weekday = check_date.weekday()
                        
                        if weekday in allowed_weekdays and event.start_time <= check_date < target_date:
                            occurrence = datetime(
                                check_date.year,
                                check_date.month,
                                check_date.day,
                                event.start_time.hour,
                                event.start_time.minute,
                                event.start_time.second
                            )
                            if occurrence < target_date:
                                previous = occurrence
                
                week_number += 1
        else:
            # Weekly without specific days
            while current < target_date:
                previous = current
                current += timedelta(weeks=event.repeat_interval)
    
    elif event.repeat_type == RepeatTypeEnum.monthly:
        if relativedelta:
            while current < target_date:
                previous = current
                current += relativedelta(months=event.repeat_interval)
        else:
            while current < target_date:
                previous = current
                current += timedelta(days=30 * event.repeat_interval)
    
    elif event.repeat_type == RepeatTypeEnum.yearly:
        if relativedelta:
            while current < target_date:
                previous = current
                current += relativedelta(years=event.repeat_interval)
        else:
            while current < target_date:
                previous = current
                current += timedelta(days=365 * event.repeat_interval)
    
    return previous


def generate_repeat_instances(
    event: Event, 
    start_date: datetime, 
    end_date: datetime,
    timezone_offset_minutes: Optional[int],
    exceptions: List[EventException],
    modified_events_cache: Dict[int, Event]
) -> List[dict]:
    """
    Generate repeat instances for an event within a date range.
    FIXED: Optimized to use preloaded exceptions and cache
    """
    instances = []
    
    if event.repeat_type == RepeatTypeEnum.none:
        return instances
    
    duration = event.end_time - event.start_time
    
    # Determine repeat end date
    if event.repeat_end_type == RepeatEndTypeEnum.date and event.repeat_until:
        repeat_end = event.repeat_until
    elif event.repeat_end_type == RepeatEndTypeEnum.count and event.repeat_count:
        repeat_end = end_date  # We'll break when count is reached
    else:
        repeat_end = end_date
    
    if event.repeat_type == RepeatTypeEnum.weekly and event.repeat_days:
        # Handle weekly with specific days (e.g., Mon-Fri)
        allowed_weekdays = set(int(d) for d in event.repeat_days.split(','))
        
        # FIXED: Count ALL week cycles, not just visible ones
        week_cycle_count = 0
        max_week_cycles = event.repeat_count if event.repeat_end_type == RepeatEndTypeEnum.count else None
        
        week_number = 0
        
        while True:
            # Get the start of this week interval
            week_start = event.start_time + timedelta(days=week_number * 7)
            
            # Check if we've gone past the repeat end date
            if week_start > repeat_end:
                break
            
            # Only process weeks that match our interval
            if week_number % event.repeat_interval == 0:
                # FIXED: Check week cycle limit BEFORE processing this week
                if max_week_cycles is not None and week_cycle_count >= max_week_cycles:
                    break
                
                # Increment counter for this week cycle
                week_cycle_count += 1
                
                # Generate instances for each selected weekday in this week
                for day_offset in range(7):
                    check_date = week_start + timedelta(days=day_offset)
                    weekday = check_date.weekday()  # 0=Monday, 6=Sunday
                    
                    # Check if this weekday is selected and within range
                    if weekday in allowed_weekdays and check_date >= event.start_time:
                        instance_start = datetime(
                            check_date.year,
                            check_date.month,
                            check_date.day,
                            event.start_time.hour,
                            event.start_time.minute,
                            event.start_time.second
                        )
                        instance_end = instance_start + duration
                        
                        # Check if within repeat_until
                        if event.repeat_end_type == RepeatEndTypeEnum.date and event.repeat_until:
                            if instance_start > event.repeat_until:
                                continue
                        
                        # Skip the original occurrence
                        if instance_start == event.start_time:
                            continue
                        
                        # Only include if within requested date range
                        if instance_end >= start_date and instance_start <= end_date:
                            # Check if this occurrence was deleted
                            if should_include_occurrence(event, instance_start, exceptions):
                                # Check if this occurrence was modified
                                modified_event = get_modified_event_for_occurrence(
                                    event, instance_start, exceptions, modified_events_cache
                                )
                                
                                if modified_event:
                                    instance_dict = event_to_dict_with_timezone(
                                        modified_event, timezone_offset_minutes
                                    )
                                    instance_dict["is_repeat_instance"] = True
                                    instance_dict["original_start"] = event.start_time
                                else:
                                    instance_dict = {
                                        "id": event.id,
                                        "user_id": event.user_id,
                                        "parent_event_id": event.parent_event_id,
                                        "title": event.title,
                                        "description": event.description,
                                        "start_time": instance_start,
                                        "end_time": instance_end,
                                        "all_day": event.all_day,
                                        "repeat_type": event.repeat_type.value,
                                        "repeat_interval": event.repeat_interval,
                                        "repeat_days": event.repeat_days,
                                        "repeat_until": event.repeat_until,
                                        "repeat_end_type": event.repeat_end_type.value,
                                        "repeat_count": event.repeat_count,
                                        "created_by": event.created_by,
                                        "created_at": event.created_at,
                                        "updated_at": event.updated_at,
                                        "is_repeat_instance": True,
                                        "original_start": event.start_time
                                    }
                                    instance_dict = apply_timezone_to_event(
                                        instance_dict, timezone_offset_minutes
                                    )
                                
                                instances.append(instance_dict)
            
            # Move to next week
            week_number += 1
        
        return instances
    
    # Handle other repeat types (daily, monthly, yearly, weekly without specific days)
    # FIXED: Count ALL occurrences, not just visible ones
    occurrence_count = 0
    current_date = event.start_time
    
    # Move to first occurrence after the original
    if event.repeat_type == RepeatTypeEnum.daily:
        current_date += timedelta(days=event.repeat_interval)
    elif event.repeat_type == RepeatTypeEnum.weekly:
        current_date += timedelta(weeks=event.repeat_interval)
    elif event.repeat_type == RepeatTypeEnum.monthly:
        if relativedelta:
            current_date += relativedelta(months=event.repeat_interval)
        else:
            current_date += timedelta(days=30 * event.repeat_interval)
    elif event.repeat_type == RepeatTypeEnum.yearly:
        if relativedelta:
            current_date += relativedelta(years=event.repeat_interval)
        else:
            current_date += timedelta(days=365 * event.repeat_interval)
    
    while current_date <= min(repeat_end, end_date):
        # FIXED: Check count limit BEFORE generating
        if event.repeat_end_type == RepeatEndTypeEnum.count and event.repeat_count:
            if occurrence_count >= event.repeat_count:
                break
        
        # FIXED: Increment count for ALL occurrences, not just visible ones
        occurrence_count += 1
        
        instance_end = current_date + duration
        
        # Check if instance overlaps with requested range
        if instance_end >= start_date and current_date <= end_date:
            # Check if this occurrence was deleted
            if should_include_occurrence(event, current_date, exceptions):
                # Check if this occurrence was modified
                modified_event = get_modified_event_for_occurrence(
                    event, current_date, exceptions, modified_events_cache
                )
                
                if modified_event:
                    instance_dict = event_to_dict_with_timezone(modified_event, timezone_offset_minutes)
                    instance_dict["is_repeat_instance"] = True
                    instance_dict["original_start"] = event.start_time
                else:
                    instance_dict = {
                        "id": event.id,
                        "user_id": event.user_id,
                        "parent_event_id": event.parent_event_id,
                        "title": event.title,
                        "description": event.description,
                        "start_time": current_date,
                        "end_time": instance_end,
                        "all_day": event.all_day,
                        "repeat_type": event.repeat_type.value,
                        "repeat_interval": event.repeat_interval,
                        "repeat_days": event.repeat_days,
                        "repeat_until": event.repeat_until,
                        "repeat_end_type": event.repeat_end_type.value,
                        "repeat_count": event.repeat_count,
                        "created_by": event.created_by,
                        "created_at": event.created_at,
                        "updated_at": event.updated_at,
                        "is_repeat_instance": True,
                        "original_start": event.start_time
                    }
                    instance_dict = apply_timezone_to_event(instance_dict, timezone_offset_minutes)
                
                instances.append(instance_dict)
        
        # Move to next occurrence
        if event.repeat_type == RepeatTypeEnum.daily:
            current_date += timedelta(days=event.repeat_interval)
        elif event.repeat_type == RepeatTypeEnum.weekly:
            current_date += timedelta(weeks=event.repeat_interval)
        elif event.repeat_type == RepeatTypeEnum.monthly:
            if relativedelta:
                current_date += relativedelta(months=event.repeat_interval)
            else:
                current_date += timedelta(days=30 * event.repeat_interval)
        elif event.repeat_type == RepeatTypeEnum.yearly:
            if relativedelta:
                current_date += relativedelta(years=event.repeat_interval)
            else:
                current_date += timedelta(days=365 * event.repeat_interval)
        else:
            break
    
    return instances


def validate_repeat_days(repeat_days: Optional[str]) -> None:
    """Validate repeat_days format and values"""
    if not repeat_days:
        return
    
    try:
        days = [int(d.strip()) for d in repeat_days.split(',') if d.strip()]
        if not all(0 <= d <= 6 for d in days):
            raise ValueError("Days must be between 0 and 6")
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repeat_days format: {str(e)}"
        )


@event_router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Create a new event"""
    
    # Validate repeat_days if provided
    if data.repeat_days:
        validate_repeat_days(data.repeat_days)
    
    # Convert times from user timezone to UTC
    start_time_utc = convert_user_to_utc_timezone(data.start_time, timezone_offset)
    end_time_utc = convert_user_to_utc_timezone(data.end_time, timezone_offset)
    
    if end_time_utc <= start_time_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    repeat_until_utc = None
    if data.repeat_end_type == RepeatEndTypeEnum.date and data.repeat_until:
        repeat_until_utc = convert_user_to_utc_timezone(data.repeat_until, timezone_offset)
        if repeat_until_utc <= start_time_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repeat until date must be after start time"
            )
    
    # Validate repeat_count
    if data.repeat_end_type == RepeatEndTypeEnum.count and not data.repeat_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repeat count is required when end type is 'count'"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == data.user_id, User.deleted_at == None).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if current_user["role_id"] != 1 and data.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create events for yourself"
        )
    
    event = Event(
        user_id=data.user_id,
        title=data.title,
        description=data.description,
        start_time=start_time_utc,
        end_time=end_time_utc,
        all_day=data.all_day,
        repeat_type=data.repeat_type,
        repeat_interval=data.repeat_interval,
        repeat_days=data.repeat_days,
        repeat_until=repeat_until_utc,
        repeat_end_type=data.repeat_end_type,
        repeat_count=data.repeat_count,
        created_by=current_user["user_id"]
    )
    
    try:
        db.add(event)
        db.commit()
        db.refresh(event)
        
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@event_router.get("/", response_model=List[EventResponse])
async def list_events(
    user_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    include_repeating: bool = Query(True),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """List events with optional filters"""
    
    start_date_utc = convert_user_to_utc_timezone(start_date, timezone_offset) if start_date else None
    end_date_utc = convert_user_to_utc_timezone(end_date, timezone_offset) if end_date else None
    
    query = db.query(Event)
    
    if current_user["role_id"] != 1:
        query = query.filter(Event.user_id == current_user["user_id"])
    else:
        user_filter = user_id if user_id is not None else current_user["user_id"]
        query = query.filter(Event.user_id == user_filter)
    
    # FIXED: Simplified filtering - only filter in query, not double-filter
    if start_date_utc and end_date_utc:
        query = query.filter(
            Event.start_time <= end_date_utc
        ).filter(
            (Event.repeat_type == RepeatTypeEnum.none) |
            (Event.repeat_end_type == RepeatEndTypeEnum.never) |
            (Event.repeat_until.is_(None)) |
            (Event.repeat_until >= start_date_utc)
        )
    elif start_date_utc:
        query = query.filter(Event.start_time >= start_date_utc)
    elif end_date_utc:
        query = query.filter(Event.end_time <= end_date_utc)
    
    events = query.order_by(Event.start_time).all()
    
    # FIXED: Preload all exceptions to avoid N+1 queries
    event_ids = [e.id for e in events]
    exceptions_list = db.query(EventException).filter(
        EventException.event_id.in_(event_ids)
    ).all() if event_ids else []
    
    # Group exceptions by event_id
    exceptions_by_event: Dict[int, List[EventException]] = {}
    for exc in exceptions_list:
        if exc.event_id not in exceptions_by_event:
            exceptions_by_event[exc.event_id] = []
        exceptions_by_event[exc.event_id].append(exc)
    
    # FIXED: Preload all modified events
    modified_event_ids = [exc.modified_event_id for exc in exceptions_list if exc.modified_event_id]
    modified_events = db.query(Event).filter(Event.id.in_(modified_event_ids)).all() if modified_event_ids else []
    modified_events_cache = {e.id: e for e in modified_events}
    
    result_events = []
    
    for event in events:
        # FIXED: Remove double filtering - event already matches query filters
        event_dict = event_to_dict_with_timezone(event, timezone_offset)
        result_events.append(EventResponse(**event_dict))
        
        if include_repeating and start_date_utc and end_date_utc and event.repeat_type != RepeatTypeEnum.none:
            event_exceptions = exceptions_by_event.get(event.id, [])
            instances = generate_repeat_instances(
                event, start_date_utc, end_date_utc, timezone_offset, 
                event_exceptions, modified_events_cache
            )
            result_events.extend([EventResponse(**inst) for inst in instances])
    
    return result_events


@event_router.get("/{event_id}", response_model=EventWithUser)
async def get_event(
    event_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Get details of a specific event"""
    
    event = db.query(Event).options(
        joinedload(Event.user),
        joinedload(Event.creator)
    ).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if current_user["role_id"] != 1 and event.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own events"
        )
    
    event_dict = event_to_dict_with_timezone(event, timezone_offset)
    
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
async def update_event(
    event_id: int,
    request_body: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Update an event with scope control (this/future/all)"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # FIXED: Permission check - admins can edit anything, non-admins can edit their own events
    if current_user["role_id"] != 1 and event.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own events"
        )
    
    # Extract scope from request body
    scope = request_body.pop('scope', 'all')
    occurrence_date_str = request_body.pop('occurrence_date', None)
    occurrence_date = None
    if occurrence_date_str:
        occurrence_date = datetime.fromisoformat(occurrence_date_str.replace('Z', '+00:00'))
    
    # Remove fields that shouldn't be updated
    request_body.pop('id', None)
    request_body.pop('created_by', None)
    request_body.pop('created_at', None)
    request_body.pop('updated_at', None)
    request_body.pop('parent_event_id', None)
    
    if not request_body:
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
    
    # Validate repeat_days if being updated
    if "repeat_days" in request_body and request_body["repeat_days"]:
        validate_repeat_days(request_body["repeat_days"])
    
    # Convert times
    if "start_time" in request_body:
        request_body["start_time"] = convert_user_to_utc_timezone(
            datetime.fromisoformat(request_body["start_time"].replace('Z', '+00:00')),
            timezone_offset
        )
    if "end_time" in request_body:
        request_body["end_time"] = convert_user_to_utc_timezone(
            datetime.fromisoformat(request_body["end_time"].replace('Z', '+00:00')),
            timezone_offset
        )
    if "repeat_until" in request_body and request_body["repeat_until"]:
        request_body["repeat_until"] = convert_user_to_utc_timezone(
            datetime.fromisoformat(request_body["repeat_until"].replace('Z', '+00:00')),
            timezone_offset
        )
    
    # FIXED: Validate enum values with proper error handling
    if "repeat_type" in request_body:
        try:
            RepeatTypeEnum[request_body["repeat_type"]]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid repeat_type: {request_body['repeat_type']}"
            )
    
    if "repeat_end_type" in request_body:
        try:
            RepeatEndTypeEnum[request_body["repeat_end_type"]]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid repeat_end_type: {request_body['repeat_end_type']}"
            )
    
    # Validate times
    if "start_time" in request_body or "end_time" in request_body:
        start = request_body.get("start_time", event.start_time)
        end = request_body.get("end_time", event.end_time)
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
    
    try:
        if event.repeat_type == RepeatTypeEnum.none or scope == "all":
            # Update all
            for field, value in request_body.items():
                setattr(event, field, value)
            db.commit()
            db.refresh(event)
            
        elif scope == "this":
            # Update just this occurrence
            if not occurrence_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="occurrence_date is required for 'this' scope"
                )
            
            occurrence_date_utc = convert_user_to_utc_timezone(occurrence_date, timezone_offset)
            
            # Create a new standalone event for this occurrence
            duration = event.end_time - event.start_time
            new_start = occurrence_date_utc
            new_end = new_start + duration
            
            # Apply updates
            if "start_time" in request_body:
                new_start = request_body["start_time"]
            if "end_time" in request_body:
                new_end = request_body["end_time"]
            
            new_event = Event(
                user_id=event.user_id,
                title=request_body.get("title", event.title),
                description=request_body.get("description", event.description),
                start_time=new_start,
                end_time=new_end,
                all_day=request_body.get("all_day", event.all_day),
                repeat_type=RepeatTypeEnum.none,
                repeat_interval=1,
                repeat_days=None,
                repeat_until=None,
                repeat_end_type=RepeatEndTypeEnum.never,
                repeat_count=None,
                created_by=current_user["user_id"]
            )
            db.add(new_event)
            db.flush()
            
            # Create exception
            exception = EventException(
                event_id=event.id,
                exception_date=occurrence_date_utc.date(),
                exception_type=ExceptionTypeEnum.modified,
                modified_event_id=new_event.id
            )
            db.add(exception)
            db.commit()
            db.refresh(new_event)
            
            response_dict = event_to_dict_with_timezone(new_event, timezone_offset)
            return EventResponse(**response_dict)
            
        elif scope == "future":
            # Update this and future occurrences
            if not occurrence_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="occurrence_date is required for 'future' scope"
                )
            
            occurrence_date_utc = convert_user_to_utc_timezone(occurrence_date, timezone_offset)
            
            # FIXED: Calculate the actual previous occurrence
            previous_occurrence = calculate_previous_occurrence(event, occurrence_date_utc)
            event.repeat_until = previous_occurrence
            event.repeat_end_type = RepeatEndTypeEnum.date
            
            # Create new event starting from this occurrence
            duration = event.end_time - event.start_time
            new_start = occurrence_date_utc
            new_end = new_start + duration
            
            if "start_time" in request_body:
                new_start = request_body["start_time"]
            if "end_time" in request_body:
                new_end = request_body["end_time"]
            
            new_event = Event(
                parent_event_id=event.id,
                user_id=event.user_id,
                title=request_body.get("title", event.title),
                description=request_body.get("description", event.description),
                start_time=new_start,
                end_time=new_end,
                all_day=request_body.get("all_day", event.all_day),
                repeat_type=RepeatTypeEnum[request_body.get("repeat_type", event.repeat_type.value)],
                repeat_interval=request_body.get("repeat_interval", event.repeat_interval),
                repeat_days=request_body.get("repeat_days", event.repeat_days),
                repeat_until=request_body.get("repeat_until", event.repeat_until),
                repeat_end_type=RepeatEndTypeEnum[request_body.get("repeat_end_type", event.repeat_end_type.value)],
                repeat_count=request_body.get("repeat_count", event.repeat_count),
                created_by=current_user["user_id"]
            )
            db.add(new_event)
            db.commit()
            db.refresh(new_event)
            
            response_dict = event_to_dict_with_timezone(new_event, timezone_offset)
            return EventResponse(**response_dict)
        
        response_dict = event_to_dict_with_timezone(event, timezone_offset)
        return EventResponse(**response_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@event_router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    request_body: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Delete an event with scope control (this/future/all)"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # FIXED: Permission check - admins can delete anything, non-admins can delete their own events
    if current_user["role_id"] != 1 and event.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own events"
        )
    
    # Extract scope from request body
    scope = request_body.get('scope', 'all')
    occurrence_date_str = request_body.get('occurrence_date')
    occurrence_date = None
    if occurrence_date_str:
        occurrence_date = datetime.fromisoformat(occurrence_date_str.replace('Z', '+00:00'))
    
    try:
        if event.repeat_type == RepeatTypeEnum.none or scope == "all":
            # Delete all
            db.delete(event)
            db.commit()
            return {"message": "Event deleted successfully"}
            
        elif scope == "this":
            # Delete just this occurrence
            if not occurrence_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="occurrence_date is required for 'this' scope"
                )
            
            occurrence_date_utc = convert_user_to_utc_timezone(occurrence_date, timezone_offset)
            
            # Create exception
            exception = EventException(
                event_id=event.id,
                exception_date=occurrence_date_utc.date(),
                exception_type=ExceptionTypeEnum.deleted,
                modified_event_id=None
            )
            db.add(exception)
            db.commit()
            return {"message": "Event occurrence deleted successfully"}
            
        elif scope == "future":
            # Delete this and future occurrences
            if not occurrence_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="occurrence_date is required for 'future' scope"
                )
            
            occurrence_date_utc = convert_user_to_utc_timezone(occurrence_date, timezone_offset)
            
            # FIXED: Calculate the actual previous occurrence
            previous_occurrence = calculate_previous_occurrence(event, occurrence_date_utc)
            event.repeat_until = previous_occurrence
            event.repeat_end_type = RepeatEndTypeEnum.date
            
            db.commit()
            return {"message": "Future event occurrences deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )


@event_router.post("/{event_id}/copy", response_model=EventCopyResponse, status_code=status.HTTP_201_CREATED)
async def copy_event(
    event_id: int,
    data: EventCopyCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Copy an event to another user/date"""
    
    if current_user["role_id"] != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can copy events"
        )
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    target_user = db.query(User).filter(
        User.id == data.target_user_id,
        User.deleted_at == None
    ).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )
    
    target_date_utc = convert_user_to_utc_timezone(data.target_date, timezone_offset)
    time_diff = target_date_utc - event.start_time
    
    new_event = Event(
        user_id=data.target_user_id,
        title=event.title,
        description=event.description,
        start_time=event.start_time + time_diff,
        end_time=event.end_time + time_diff,
        all_day=event.all_day,
        repeat_type=RepeatTypeEnum.none,
        repeat_interval=1,
        repeat_days=None,
        repeat_until=None,
        repeat_end_type=RepeatEndTypeEnum.never,
        repeat_count=None,
        created_by=current_user["user_id"]
    )
    
    try:
        db.add(new_event)
        db.flush()
        
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
async def bulk_copy_event(
    event_id: int,
    data: EventBulkCopyCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    timezone_offset: Optional[int] = Header(None, alias="X-Timezone-Offset")
):
    """Copy an event to multiple users and/or dates (Admin only)"""
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
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
                target_date_utc = convert_user_to_utc_timezone(target_date, timezone_offset)
                time_diff = target_date_utc - event.start_time
                
                new_event = Event(
                    user_id=user_id,
                    title=event.title,
                    description=event.description,
                    start_time=event.start_time + time_diff,
                    end_time=event.end_time + time_diff,
                    all_day=event.all_day,
                    repeat_type=RepeatTypeEnum.none,
                    repeat_interval=1,
                    repeat_days=None,
                    repeat_until=None,
                    repeat_end_type=RepeatEndTypeEnum.never,
                    repeat_count=None,
                    created_by=current_user["user_id"]
                )
                db.add(new_event)
                db.flush()
                
                event_copy = EventCopy(
                    event_id=event_id,
                    user_id=user_id,
                    date=target_date_utc
                )
                db.add(event_copy)
                db.flush()
                copies.append(event_copy)
        
        db.commit()
        
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
async def get_event_copies(
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