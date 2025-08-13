from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class MessageTypeEnum(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"

class MessageBase(BaseModel):
    conversation_id: int
    sender_id: int
    message_type: MessageTypeEnum = MessageTypeEnum.text
    content: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None

class MessageCreate(MessageBase):
    pass

class MessageUpdate(BaseModel):
    content: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None

class MessageResponse(MessageBase):
    id: int
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    trainer_id: int
    client_id: int

class ConversationCreate(ConversationBase):
    pass

class ConversationUpdate(BaseModel):
    last_message_id: Optional[int] = None
    last_message_at: Optional[datetime] = None

class ConversationResponse(ConversationBase):
    id: int
    last_message_id: Optional[int] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Additional UI fields
    client_name: Optional[str] = None
    client_avatar: Optional[str] = None
    last_message_text: Optional[str] = None
    has_unread_messages: bool = False
    unread_count: int = 0
    
    class Config:
        from_attributes = True