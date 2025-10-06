from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    messages = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey("chat_threads.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)  # Store file URL here
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, 
        default=func.current_timestamp(), 
        onupdate=func.current_timestamp()
    )

    # Relationships
    thread = relationship("ChatThread", back_populates="messages")