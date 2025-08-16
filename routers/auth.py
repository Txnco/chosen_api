from fastapi import APIRouter, Depends
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

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@auth_router.post("/register")
def register(first_name: str, last_name:str, email: str, password: str,  db: Session = Depends(get_db), current_user=Depends(require_admin)):
    hashed_pw = pwd_context.hash(password)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists."
        )

    hashed_pw = pwd_context.hash(password)
    new_user = User(
        email=email,
        password_hash=hashed_pw,
        first_name=first_name,
        last_name=last_name,
        role_id=2
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User created by user {current_user['user_id']}"}


class LoginRequest(BaseModel):
    email: str
    password: str

@auth_router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email= data.email
    password = data.password
    user = db.query(User).filter(User.email == email, User.deleted_at == None).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"user_id": user.id, "role_id": user.role_id})
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get('/validate')
def validate_token(current_user=Depends(get_current_user)):
    return{
        "user_id": current_user["user_id"],
        "role_id": current_user["role_id"],
        "valid": True
    }

# @auth_router.post('/logout')
# def logout(current_user=Depends(get_current_user)):
    