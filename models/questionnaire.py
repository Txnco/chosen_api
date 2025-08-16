from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Enum, ForeignKey
from database import Base
from sqlalchemy.sql import func

import enum


class WorkoutEnvironmentEnum(enum.Enum):
    gym = "gym"
    home = "home"
    outdoor = "outdoor"
    both = "both"

class WorkShiftEnum(enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    night = "night"
    split = "split"
    flexible = "flexible"

class UserQuestionnaire(Base):
    __tablename__ = "user_questionnaire"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    birthday = Column(DateTime, nullable=True)  # Changed from age to birthday
    health_issues = Column(Text, nullable=True)
    bad_habits = Column(Text, nullable=True)
    workout_environment = Column(Enum(WorkoutEnvironmentEnum), nullable=True)
    work_shift = Column(Enum(WorkShiftEnum), nullable=True)
    wake_up_time = Column(String(10), nullable=True)
    sleep_time = Column(String(10), nullable=True)
    morning_routine = Column(Text, nullable=True)
    evening_routine = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )