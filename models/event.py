# models/event.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
import enum


class RepeatTypeEnum(enum.Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"
    custom = "custom"


class RepeatEndTypeEnum(enum.Enum):
    never = "never"
    date = "date"
    count = "count"


class ExceptionTypeEnum(enum.Enum):
    deleted = "deleted"
    modified = "modified"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent_event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    all_day = Column(Boolean, nullable=False, default=False)
    repeat_type = Column(Enum(RepeatTypeEnum), nullable=False, default=RepeatTypeEnum.none)
    repeat_interval = Column(Integer, nullable=False, default=1)
    repeat_days = Column(String(50), nullable=True)
    repeat_until = Column(DateTime, nullable=True)
    repeat_end_type = Column(Enum(RepeatEndTypeEnum), nullable=False, default=RepeatEndTypeEnum.never)
    repeat_count = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )

    # Relationships - FIX: Specify foreign_keys explicitly
    user = relationship("User", foreign_keys=[user_id], backref="events")
    creator = relationship("User", foreign_keys=[created_by])
    copies = relationship("EventCopy", back_populates="event", cascade="all, delete-orphan")
    exceptions = relationship(
        "EventException", 
        back_populates="event", 
        foreign_keys="[EventException.event_id]",  # Specify which FK to use
        cascade="all, delete-orphan"
    )
    parent_event = relationship("Event", remote_side=[id], foreign_keys=[parent_event_id])


class EventCopy(Base):
    __tablename__ = "event_copies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    event = relationship("Event", back_populates="copies")
    user = relationship("User", backref="event_copies")


class EventException(Base):
    __tablename__ = "event_exceptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    exception_date = Column(Date, nullable=False, index=True)
    exception_type = Column(Enum(ExceptionTypeEnum), nullable=False)
    modified_event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    event = relationship("Event", back_populates="exceptions", foreign_keys=[event_id])
    modified_event = relationship("Event", foreign_keys=[modified_event_id])