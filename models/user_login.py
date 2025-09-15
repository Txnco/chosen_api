from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

class UserLogin(Base):
    __tablename__ = "user_logins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    login_time = Column(DateTime, server_default=func.now(), nullable=False)
    logout_time = Column(DateTime, nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="login_sessions")