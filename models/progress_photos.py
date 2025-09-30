from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from database import Base
import enum

class PhotoAngleEnum(enum.Enum):
    front = "front"
    side = "side"
    back = "back"

class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    angle = Column(SQLEnum(PhotoAngleEnum), nullable=False)
    image_url = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )
    deleted_at = Column(DateTime, nullable=True)