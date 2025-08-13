from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")
    email: EmailStr = Field(..., description="User's email address")
    role_id: int = Field(default=2, description="User's role ID")

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=6, max_length=255, description="User's password")

class UserUpdate(BaseModel):
    """Schema for updating an existing user"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's last name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    role_id: Optional[int] = Field(None, description="User's role ID")

class UserPasswordUpdate(BaseModel):
    """Schema for updating user password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, max_length=255, description="New password")

class UserPasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="User's email address")

class UserPasswordResetConfirm(BaseModel):
    """Schema for confirming password reset"""
    reset_token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=6, max_length=255, description="New password")

class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

class UserInDB(UserResponse):
    """Schema for user stored in database (includes sensitive data)"""
    password_hash: str
    reset_token: Optional[str] = None
    reset_token_expires_at: Optional[datetime] = None

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class UserProfile(UserResponse):
    """Schema for user profile (public information)"""
    pass