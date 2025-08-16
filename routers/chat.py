from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from auth.jwt import get_current_user
from models.user import User
from models.chat import ChatMessage, ChatThread

chat_router = APIRouter(prefix="/chat", tags=["Chat"])

@chat_router.get('/threads')
def list_threads(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_role = current_user['role_id']
    user_id = current_user['user_id']
    
    if user_role == 2:  # Client role
        # For clients: find their thread or create one with trainer_id=1
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
            return [new_thread]
        
        return [thread]
    
    elif user_role == 1:  # Admin/Trainer role
        # For trainers: list all their threads
        threads = db.query(ChatThread).filter(
            ChatThread.trainer_id == user_id,
            ChatThread.deleted_at == None
        ).all()
        
        return threads
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role"
        )
    

@chat_router.post('/message')
def send_message(thread_id: int, body: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user['user_id']
    
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
        body=body
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message