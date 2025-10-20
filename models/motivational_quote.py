"""
File 1 of 3: models/motivational_quote.py
Copy this entire file to your models folder
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class MotivationalQuote(Base):
    __tablename__ = "motivational_quotes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quote = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    times_shown = Column(Integer, nullable=False, default=0)
    last_shown_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )
    deleted_at = Column(DateTime, nullable=True)

