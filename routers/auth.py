from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal
from passlib.context import CryptContext
from auth.jwt import create_access_token
from auth.jwt import require_admin
from auth.jwt import get_current_user
from models.user import User
from pydantic import BaseModel
from database import get_db
from typing import Optional
from models.user_login import UserLogin
from functions.upload import upload_profile_image
from schema.notification import get_default_notification_preferences
from functions.send_mail import send_welcome_email
import secrets
import string
from datetime import datetime, timezone


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

@auth_router.post("/register")
def register(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None),  
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    if not password or not password.strip() or password.strip().lower() == "undefined":
        password = generate_random_password()
    else:
        password = password.strip()

    hashed_pw = pwd_context.hash(password)

    # Check if user exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists."
        )

    # Handle profile picture upload
    profile_picture_filename = None
    if profile_picture:
        try:
            profile_picture_filename = upload_profile_image(profile_picture)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload profile picture: {str(e)}"
            )

    # Create user
    new_user = User(
        email=email,
        password_hash=hashed_pw,
        first_name=first_name,
        last_name=last_name,
        role_id=2,
        profile_picture=profile_picture_filename,
        notification_preferences=get_default_notification_preferences()
    )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send email AFTER successful commit
    try:
        send_welcome_email(first_name, email, password)
    except Exception as e:
        # Email failed, but user is created — this is safest behavior
        print("SES send error:", e)

    return {
        "message": f"User created by user {current_user['user_id']}",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "role_id": new_user.role_id,
            "profile_picture": new_user.profile_picture,
        }
    }


class LoginRequest(BaseModel):
    email: str
    password: str

@auth_router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email= data.email
    password = data.password
    user = db.query(User).filter(User.email == email, User.deleted_at == None).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    login_record = UserLogin(
        user_id=user.id,
        ip_address=ip,
        user_agent=ua
    )
    db.add(login_record)
    db.commit()
    db.refresh(login_record)

    access_token = create_access_token(data={"user_id": user.id, "role_id": user.role_id})
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get('/validate')
def validate_token(current_user=Depends(get_current_user)):
    return{
        "user_id": current_user["user_id"],
        "role_id": current_user["role_id"],
        "valid": True
    }


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str


@auth_router.post('/reset-password')
def reset_password(
    data: ResetPasswordConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset user password using a valid reset token.
    This is a public endpoint that anyone can use with a valid token.
    """
    # Find user by reset token
    user = db.query(User).filter(
        User.reset_token == data.token,
        User.deleted_at == None
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token nevažeći ili je istekao"
        )

    # Check if token has expired
    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token je istekao. Molimo zatražite novi link za resetiranje."
        )

    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lozinka mora imati najmanje 6 znakova"
        )

    # Update password and clear reset token
    user.password_hash = pwd_context.hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {
        "message": "Lozinka je uspješno promijenjena. Možete se sada prijaviti.",
        "success": True
    }

# @auth_router.post('/logout')
# def logout(current_user=Depends(get_current_user)):

