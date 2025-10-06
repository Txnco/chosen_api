from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ChatThreadBase(BaseModel):
    client_id: int = Field(..., description="Client user ID")
    trainer_id: int = Field(..., description="Trainer user ID")


class ChatThreadCreate(ChatThreadBase):
    """Schema for creating a new chat thread"""
    pass


class ChatThreadUpdate(BaseModel):
    """Schema for updating an existing chat thread"""
    client_id: Optional[int] = Field(None, description="Client user ID")
    trainer_id: Optional[int] = Field(None, description="Trainer user ID")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")


class ChatThreadResponse(ChatThreadBase):
    """Schema for chat thread response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class ChatMessageBase(BaseModel):
    thread_id: int = Field(..., description="Chat thread ID")
    user_id: int = Field(..., description="User ID who sent the message")
    body: str = Field(..., max_length=65535, description="Message content")
    image_url: Optional[str] = Field(None, max_length=255, description="Image URL if message contains image")



class ChatMessageUpdate(BaseModel):
    """Schema for updating an existing chat message"""
    body: Optional[str] = Field(None, max_length=65535, description="Message content")
    image_url: Optional[str] = Field(None, max_length=255, description="Image URL if message contains image")

class ChatMessageCreate(BaseModel):
    thread_id: int = Field(..., description="Thread ID")
    body: str = Field(..., description="Message content")
    image_url: Optional[str] = Field(None, description="File URL if message has attachment")

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    thread_id: int
    user_id: int
    body: str
    image_url: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime