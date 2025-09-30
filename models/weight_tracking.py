from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from database import Base

class WeightTracking(Base):
    __tablename__ = "weight_tracking"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    weight = Column(DECIMAL(precision=5, scale=2), nullable=False)
    date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )
    deleted_at = Column(DateTime, nullable=True)