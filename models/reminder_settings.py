from sqlalchemy import Column, Integer, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func


class ReminderSettings(Base):
    __tablename__ = "reminder_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    water_reminder = Column(SmallInteger, nullable=False, default=1)
    scale_reminder = Column(SmallInteger, nullable=False, default=1)
    photo_reminder = Column(SmallInteger, nullable=False, default=1)
    plan_day_reminder = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])