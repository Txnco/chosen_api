from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi import UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from database import get_db
from auth.jwt import get_current_user
from models.user import User
from models.chat import ChatMessage, ChatThread
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

chat_router = APIRouter(prefix="/chat", tags=["Chat"])

# Pydantic models
class MessageCreate(BaseModel):
    thread_id: int
    body: str

class MarkReadRequest(BaseModel):
    message_ids: List[int]

class ThreadCreate(BaseModel):
    client_id: int

@chat_router.post('/message')
def send_message(
    message_data: MessageCreate,
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Send a message in a thread"""
    user_id = current_user['user_id']
    thread_id = message_data.thread_id
    body = message_data.body
    
    # Check if thread exists and user has access to it
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.deleted_at == None
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Check if user is part of this thread (either client or trainer)
    if user_id != thread.client_id and user_id != thread.trainer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this thread"
        )
    
    # Create new message
    new_message = ChatMessage(
        thread_id=thread_id,
        user_id=user_id,
        body=body,
        read_at=None  # New messages start as unread
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message

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
    
    # Check if user has access to this thread
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.deleted_at == None
    ).first()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Check access
    if user_id != thread.client_id and user_id != thread.trainer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
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
    
    return {
        "messages": messages,
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
    
    # Check thread access
    thread = db.query(ChatThread).filter(
        ChatThread.id == thread_id,
        ChatThread.deleted_at == None
    ).first()
    
    if not thread or (user_id != thread.client_id and user_id != thread.trainer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
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
        thread = db.query(ChatThread).filter(
            ChatThread.client_id == user_id,
            ChatThread.deleted_at == None
        ).first()
        
        if not thread:
            # Create new thread with hardcoded trainer_id=1
            new_thread = ChatThread(
                client_id=user_id,
                trainer_id=1
            )
            db.add(new_thread)
            db.commit()
            db.refresh(new_thread)
            
            # Get trainer info
            trainer = db.query(User).filter(User.id == 1).first()
            
            return [{
                "id": new_thread.id,
                "trainer_id": new_thread.trainer_id,
                "client_id": new_thread.client_id,
                "created_at": new_thread.created_at,
                "updated_at": new_thread.updated_at,
                "last_message": None,
                "last_message_at": None,
                "trainer_name": f"{trainer.first_name} {trainer.last_name}" if trainer else "Trainer",
                "has_unread_messages": False,
                "unread_count": 0
            }]
        
        # Get trainer info
        trainer = db.query(User).filter(User.id == thread.trainer_id).first()
        
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
            "trainer_name": f"{trainer.first_name} {trainer.last_name}" if trainer else "Trainer",
            "has_unread_messages": unread_count > 0,
            "unread_count": unread_count
        }]
    
    elif user_role == 1:  # Admin/Trainer role
        # Get threads with last message info
        threads = db.query(ChatThread).filter(
            ChatThread.trainer_id == user_id,
            ChatThread.deleted_at == None
        ).all()
        
        # Enhance each thread with last message info
        enhanced_threads = []
        for thread in threads:
            # Get last message
            last_message = db.query(ChatMessage).filter(
                ChatMessage.thread_id == thread.id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            # Get client info
            client = db.query(User).filter(User.id == thread.client_id).first()
            
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
                "client_name": f"{client.first_name} {client.last_name}" if client else None,
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
    
    # Get all clients (role_id = 2) who don't have threads
    query = db.query(User).filter(
        User.role_id == 2,
        User.deleted_at == None,
        ~User.id.in_(existing_client_ids) if existing_client_ids else True
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term)) |
            (User.email.ilike(search_term))
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
    
    # Verify the client exists and is a client (role_id = 2)
    client = db.query(User).filter(
        User.id == thread_data.client_id,
        User.role_id == 2,
        User.deleted_at == None
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
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
        unread_count = db.query(ChatMessage).join(ChatThread).filter(
            and_(
                ChatThread.client_id == user_id,
                ChatMessage.user_id == ChatThread.trainer_id,  # Messages from trainer
                ChatMessage.read_at == None,
                ChatThread.deleted_at == None
            )
        ).count()
    
    elif user_role == 1:  # Trainer
        # Count unread messages from all clients in trainer's threads
        unread_count = db.query(ChatMessage).join(ChatThread).filter(
            and_(
                ChatThread.trainer_id == user_id,
                ChatMessage.user_id == ChatThread.client_id,  # Messages from clients
                ChatMessage.read_at == None,
                ChatThread.deleted_at == None
            )
        ).count()
    
    else:
        unread_count = 0
    
    return {"unread_count": unread_count}

@chat_router.post('/upload')
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Upload file for messages"""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'audio/mpeg', 'audio/wav']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed"
        )
    
    # Create upload directory if it doesn't exist
    import os
    upload_dir = "uploads/chat"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    import uuid
    file_extension = file.filename.split('.')[-1] if file.filename else 'bin'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
    
    # Return file info
    return {
        "file_url": f"/uploads/chat/{unique_filename}",
        "file_name": file.filename,
        "file_size": os.path.getsize(file_path),
        "content_type": file.content_type
    }