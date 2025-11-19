# models/questionnaire.py
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Date, Time, ForeignKey, JSON
from database import Base
from sqlalchemy.sql import func

class UserQuestionnaire(Base):
    __tablename__ = "user_questionnaire"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    birthday = Column(Date, nullable=True)
    health_issues = Column(Text, nullable=True)
    bad_habits = Column(Text, nullable=True)
    workout_environment = Column(String(50), nullable=True)
    work_shifts = Column(JSON, nullable=True)  # Changed to JSON array
    wake_up_time = Column(Time, nullable=True)
    sleep_time = Column(Time, nullable=True)
    morning_routine = Column(Text, nullable=True)
    evening_routine = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )