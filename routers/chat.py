from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from fastapi import UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from database import get_db
from auth.jwt import get_current_user
from models.user import User
from models.chat import ChatMessage, ChatThread
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from pathlib import Path
import uuid
import shutil
from config import settings
import logging

from schema.chat import (
    ChatThreadCreate,
    ChatThreadResponse,
    ChatMessageCreate,
    ChatMessageResponse,
)
from functions.fcm import FCMService

logger = logging.getLogger("chosen_api")

chat_router = APIRouter(prefix="/chat", tags=["Chat"])

upload_dir = Path(settings.UPLOAD_URL) / "uploads" / "chat"

# Pydantic models
class MessageCreate(BaseModel):
    thread_id: int
    body: str

class MarkReadRequest(BaseModel):
    message_ids: List[int]

class ThreadCreate(BaseModel):
    client_id: int

def verify_thread_access(thread_id: int, user_id: int, user_role: int, db: Session):
    """Verify thread exists, user has access, and both parties are not deleted"""
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.deleted_at == None
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Verify both users in the thread are not deleted
    client = db.query(User).filter(
        User.id == thread.client_id,
        User.deleted_at == None
    ).first()
    
    trainer = db.query(User).filter(
        User.id == thread.trainer_id,
        User.deleted_at == None
    ).first()
    
    if not client or not trainer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread participants no longer available"
        )
    
    # Verify user has access to this thread
    if user_id not in [thread.client_id, thread.trainer_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this thread"
        )
    
    return thread, client, trainer

@chat_router.post('/message', response_model=ChatMessageResponse)
def send_message(
    data: ChatMessageCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a thread"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Verify thread access and user validity
    thread, client, trainer = verify_thread_access(data.thread_id, user_id, user_role, db)
    
    try:
        # Create message (store only filename, not full path)
        message = ChatMessage(
            thread_id=data.thread_id,
            user_id=user_id,
            body=data.body,
            image_url=data.image_url  # This should be just the filename now
        )
        
        db.add(message)
        
        # Update thread's updated_at
        thread.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        # 🆕 Send FCM notification to recipient
        sender = db.query(User).filter(User.id == user_id).first()
        recipient_id = thread.client_id if user_role == 1 else thread.trainer_id
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        if recipient and recipient.fcm_token:
            sender_name = f"{sender.first_name} {sender.last_name}"
            FCMService.send_message_notification(
                fcm_token=recipient.fcm_token,
                sender_name=sender_name,
                message_body=data.body,
                thread_id=data.thread_id,
                sender_id=user_id
            )
            logger.info(f"📱 FCM notification sent to user {recipient_id}", extra={'color': True})
        else:
            logger.info(f"⚠️ No FCM token for user {recipient_id}, skipping notification")
        
        return message
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@chat_router.get('/threads/{thread_id}/messages')
def get_thread_messages(
    thread_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific thread with pagination"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Verify thread access and user validity
    thread, client, trainer = verify_thread_access(thread_id, user_id, user_role, db)
    
    # Get messages with pagination
    offset = (page - 1) * limit
    messages = db.query(ChatMessage).filter(
        ChatMessage.thread_id == thread_id
    ).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
    
    # Auto-mark messages as read when user opens the chat
    # Mark all messages from OTHER users as read
    other_user_messages = db.query(ChatMessage).filter(
        and_(
            ChatMessage.thread_id == thread_id,
            ChatMessage.user_id != user_id,
            ChatMessage.read_at == None
        )
    ).all()
    
    if other_user_messages:
        for message in other_user_messages:
            message.read_at = datetime.utcnow()
        db.commit()
    
    # Get total count for pagination info
    total = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).count()
    
    # Convert messages to dict and add full file URLs
    messages_with_urls = []
    for message in messages:
        message_dict = {
            "id": message.id,
            "thread_id": message.thread_id,
            "user_id": message.user_id,
            "body": message.body,
            "image_url": f"/uploads/chat/{thread_id}/{message.image_url}" if message.image_url else None,
            "read_at": message.read_at,
            "created_at": message.created_at,
            "updated_at": message.updated_at
        }
        messages_with_urls.append(message_dict)
    
    return {
        "messages": messages_with_urls,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@chat_router.post('/threads/{thread_id}/mark-read')
def mark_messages_read(
    thread_id: int,
    request: MarkReadRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark specific messages as read"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Verify thread access and user validity
    thread, client, trainer = verify_thread_access(thread_id, user_id, user_role, db)
    
    # Mark messages as read (only messages from other users)
    messages_updated = db.query(ChatMessage).filter(
        and_(
            ChatMessage.id.in_(request.message_ids),
            ChatMessage.thread_id == thread_id,
            ChatMessage.user_id != user_id,  # Only mark OTHER users' messages as read
            ChatMessage.read_at == None
        )
    ).update({"read_at": datetime.utcnow()}, synchronize_session=False)
    
    db.commit()
    
    return {"messages_marked_read": messages_updated}

@chat_router.get('/threads')
def list_threads_enhanced(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """List threads with last message information and unread counts"""
    user_role = current_user['role_id']
    user_id = current_user['user_id']
    
    if user_role == 2:  # Client role
        # Only get threads where both client and trainer are not deleted
        thread = db.query(ChatThread).join(
            User, User.id == ChatThread.trainer_id
        ).filter(
            ChatThread.client_id == user_id,
            ChatThread.deleted_at == None,
            User.deleted_at == None  # Trainer must not be deleted
        ).first()
        
        if not thread:
            # Find an active trainer (not deleted, role_id = 1)
            trainer = db.query(User).filter(
                User.role_id == 1,
                User.deleted_at == None
            ).first()
            
            if not trainer:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No active trainer available"
                )
            
            # Get client info for profile picture
            client = db.query(User).filter(
                User.id == user_id,
                User.deleted_at == None
            ).first()
            
            # Create new thread with active trainer
            new_thread = ChatThread(
                client_id=user_id,
                trainer_id=trainer.id
            )
            db.add(new_thread)
            db.commit()
            db.refresh(new_thread)
            
            return [{
                "id": new_thread.id,
                "trainer_id": new_thread.trainer_id,
                "client_id": new_thread.client_id,
                "created_at": new_thread.created_at,
                "updated_at": new_thread.updated_at,
                "last_message": None,
                "last_message_at": None,
                "trainer_name": f"{trainer.first_name} {trainer.last_name}",
                "trainer_avatar": trainer.profile_picture,
                "client_avatar": client.profile_picture if client else None,
                "has_unread_messages": False,
                "unread_count": 0
            }]
        
        # Get trainer info
        trainer = db.query(User).filter(
            User.id == thread.trainer_id,
            User.deleted_at == None
        ).first()
        
        if not trainer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trainer no longer available"
            )
        
        # Get client info for profile picture
        client = db.query(User).filter(
            User.id == user_id,
            User.deleted_at == None
        ).first()
        
        # Get last message
        last_message = db.query(ChatMessage).filter(
            ChatMessage.thread_id == thread.id
        ).order_by(ChatMessage.created_at.desc()).first()
        
        # Count unread messages from trainer
        unread_count = db.query(ChatMessage).filter(
            and_(
                ChatMessage.thread_id == thread.id,
                ChatMessage.user_id == thread.trainer_id,  # Messages from trainer
                ChatMessage.read_at == None
            )
        ).count()
        
        return [{
            "id": thread.id,
            "trainer_id": thread.trainer_id,
            "client_id": thread.client_id,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at,
            "last_message": last_message.body if last_message else None,
            "last_message_at": last_message.created_at if last_message else None,
            "trainer_name": f"{trainer.first_name} {trainer.last_name}",
            "trainer_avatar": trainer.profile_picture,
            "client_avatar": client.profile_picture if client else None,
            "has_unread_messages": unread_count > 0,
            "unread_count": unread_count
        }]
    
    elif user_role == 1:  # Admin/Trainer role
        # Get threads where both trainer and client are not deleted
        threads = db.query(ChatThread).join(
            User, User.id == ChatThread.client_id
        ).filter(
            ChatThread.trainer_id == user_id,
            ChatThread.deleted_at == None,
            User.deleted_at == None  # Client must not be deleted
        ).all()
        
        # Get trainer info for profile picture
        trainer = db.query(User).filter(
            User.id == user_id,
            User.deleted_at == None
        ).first()
        
        # Enhance each thread with last message info
        enhanced_threads = []
        for thread in threads:
            # Get last message
            last_message = db.query(ChatMessage).filter(
                ChatMessage.thread_id == thread.id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            # Get client info (already verified not deleted in query)
            client = db.query(User).filter(
                User.id == thread.client_id,
                User.deleted_at == None
            ).first()
            
            # Skip if client was deleted (additional safety check)
            if not client:
                continue
            
            # Count unread messages from client
            unread_count = db.query(ChatMessage).filter(
                and_(
                    ChatMessage.thread_id == thread.id,
                    ChatMessage.user_id == thread.client_id,  # Messages from client
                    ChatMessage.read_at == None
                )
            ).count()
            
            thread_dict = {
                "id": thread.id,
                "trainer_id": thread.trainer_id,
                "client_id": thread.client_id,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at,
                "last_message": last_message.body if last_message else None,
                "last_message_at": last_message.created_at if last_message else None,
                "client_name": f"{client.first_name} {client.last_name}",
                "client_avatar": client.profile_picture,
                "trainer_avatar": trainer.profile_picture if trainer else None,
                "has_unread_messages": unread_count > 0,
                "unread_count": unread_count
            }
            enhanced_threads.append(thread_dict)
        
        return enhanced_threads
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role"
        )

@chat_router.get('/available-clients')
def get_available_clients(
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get list of clients that don't have an existing thread with the trainer"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Only trainers/admins can access this
    if user_role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can access this endpoint"
        )
    
    # Get all client IDs that already have threads with this trainer
    existing_thread_clients = db.query(ChatThread.client_id).filter(
        ChatThread.trainer_id == user_id,
        ChatThread.deleted_at == None
    ).all()
    
    existing_client_ids = [client_id for (client_id,) in existing_thread_clients]
    
    # Get all clients (role_id = 2) who don't have threads and are not deleted
    query = db.query(User).filter(
        User.role_id == 2,
        User.deleted_at == None,  # Only active clients
        ~User.id.in_(existing_client_ids) if existing_client_ids else True
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    available_clients = query.order_by(User.first_name, User.last_name).all()
    
    return [
        {
            "user_id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "email": client.email,
            "created_at": client.created_at
        }
        for client in available_clients
    ]

@chat_router.post('/threads')
def create_thread(
    thread_data: ThreadCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat thread with a client"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Only trainers/admins can create threads
    if user_role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can create threads"
        )
    
    # Verify the client exists, is a client (role_id = 2), and is not deleted
    client = db.query(User).filter(
        User.id == thread_data.client_id,
        User.role_id == 2,
        User.deleted_at == None
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or inactive"
        )
    
    # Check if thread already exists
    existing_thread = db.query(ChatThread).filter(
        ChatThread.trainer_id == user_id,
        ChatThread.client_id == thread_data.client_id,
        ChatThread.deleted_at == None
    ).first()
    
    if existing_thread:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread already exists with this client"
        )
    
    # Create new thread
    new_thread = ChatThread(
        trainer_id=user_id,
        client_id=thread_data.client_id
    )
    
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    
    return {
        "id": new_thread.id,
        "trainer_id": new_thread.trainer_id,
        "client_id": new_thread.client_id,
        "created_at": new_thread.created_at,
        "updated_at": new_thread.updated_at,
        "client_name": f"{client.first_name} {client.last_name}",
        "last_message": None,
        "last_message_at": None,
        "has_unread_messages": False,
        "unread_count": 0
    }

@chat_router.get('/unread-count')
def get_total_unread_count(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get total unread message count for current user"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    if user_role == 2:  # Client
        # Count unread messages from trainer in client's thread
        # Only count if trainer is not deleted
        unread_count = db.query(ChatMessage).join(
            ChatThread, ChatMessage.thread_id == ChatThread.id
        ).join(
            User, User.id == ChatThread.trainer_id
        ).filter(
            and_(
                ChatThread.client_id == user_id,
                ChatMessage.user_id == ChatThread.trainer_id,  # Messages from trainer
                ChatMessage.read_at == None,
                ChatThread.deleted_at == None,
                User.deleted_at == None  # Trainer not deleted
            )
        ).count()
    
    elif user_role == 1:  # Trainer
        # Count unread messages from all clients in trainer's threads
        # Only count if client is not deleted
        unread_count = db.query(ChatMessage).join(
            ChatThread, ChatMessage.thread_id == ChatThread.id
        ).join(
            User, User.id == ChatThread.client_id
        ).filter(
            and_(
                ChatThread.trainer_id == user_id,
                ChatMessage.user_id == ChatThread.client_id,  # Messages from clients
                ChatMessage.read_at == None,
                ChatThread.deleted_at == None,
                User.deleted_at == None  # Client not deleted
            )
        ).count()
    
    else:
        unread_count = 0
    
    return {"unread_count": unread_count}

@chat_router.post('/upload')
async def upload_file(
    thread_id: int = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload file for messages organized by thread"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Verify thread access and user validity
    thread, client, trainer = verify_thread_access(thread_id, user_id, user_role, db)
    
    # Validate file type
    allowed_types = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
        'audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/ogg',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed types: images, audio, PDF, DOC"
        )
    
    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()  # Get position (file size)
    file.file.seek(0)  # Reset to beginning
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB"
        )
    
    file_path = None
    try:
        # Create thread-specific upload directory
        thread_upload_dir = upload_dir / str(thread_id)
        os.makedirs(thread_upload_dir, exist_ok=True)
        
        # Generate unique filename while preserving extension
        file_extension = ''
        if file.filename:
            file_extension = os.path.splitext(file.filename)[1]
        
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = thread_upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return ONLY the filename to be stored in DB
        # The full path will be constructed when retrieving messages
        return {
            "file_name": unique_filename,  # Store this in DB
            "file_url": f"/uploads/chat/{thread_id}/{unique_filename}",  # For immediate use
            "original_name": file.filename,
            "file_size": file_size,
            "content_type": file.content_type
        }
    
    except Exception as e:
        # Clean up file if something went wrong
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@chat_router.delete('/threads/{thread_id}')
def delete_thread(
    thread_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a thread (admin/trainer only)"""
    user_id = current_user['user_id']
    user_role = current_user['role_id']
    
    # Only trainers/admins can delete threads
    if user_role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can delete threads"
        )
    
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.trainer_id == user_id,
        ChatThread.deleted_at == None
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Soft delete
    thread.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Thread deleted successfully"}