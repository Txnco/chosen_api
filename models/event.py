from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey
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


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    all_day = Column(Boolean, nullable=False, default=False)
    repeat_type = Column(Enum(RepeatTypeEnum), nullable=False, default=RepeatTypeEnum.none)
    repeat_until = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="events")
    creator = relationship("User", foreign_keys=[created_by])
    copies = relationship("EventCopy", back_populates="event", cascade="all, delete-orphan")


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